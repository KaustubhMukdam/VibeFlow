"""
Sequential Recommendation Model — LSTM-based next-song predictor.

Given the last N songs in a session, predicts a feature embedding for the
"ideal next song" and matches it against the library via cosine similarity.

Architecture:
  Input:  sequence of 19-dim feature vectors (6 audio + 13 MFCC)
  Model:  2-layer LSTM, hidden=64, output=19-dim predicted embedding
  Match:  cosine similarity against all library songs

Graceful degradation:
  - If < MIN_SESSIONS sessions with >= MIN_SEQ_LEN songs exist, skips training
  - If no model file exists, predict_next_songs() returns empty list
  - Hybrid blend falls back to 2-way (CB + ALS) when LSTM unavailable
"""
import logging
import pickle
from pathlib import Path
from typing import Optional

import numpy as np
import torch
import torch.nn as nn
from torch.utils.data import Dataset, DataLoader
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.preprocessing import StandardScaler

from db import SessionLocal
from db.models import Song, ListeningHistory

logger = logging.getLogger(__name__)

# ── Config ───────────────────────────────────────────────────────────────────
FEATURE_DIM = 19       # 6 audio features + 13 MFCC means
HIDDEN_DIM = 64
NUM_LAYERS = 2
SEQ_LENGTH = 5         # Use last 5 songs to predict the next
MIN_SESSIONS = 5       # Minimum sessions required to train
MIN_SEQ_LEN = 3        # Minimum songs per session to be usable
EPOCHS = 30
BATCH_SIZE = 16
LR = 0.001
DROPOUT = 0.2

MODEL_PATH = Path("models/saved/sequential_model.pt")
SCALER_PATH = Path("models/saved/sequential_scaler.pkl")


# ── Feature extraction (shared with bandit) ──────────────────────────────────
def _song_to_features(song: Song) -> np.ndarray:
    """Extract a 19-dim feature vector from a Song ORM object."""
    mfcc = song.mfcc_vector if isinstance(song.mfcc_vector, list) else [0.0] * 13
    mfcc_13 = (mfcc[:13] + [0.0] * 13)[:13]

    audio = [
        song.energy or 0.0,
        (song.tempo or 120) / 200.0,
        song.acousticness or 0.0,
        song.instrumentalness or 0.0,
        song.speechiness or 0.0,
        min(1.0, max(0.0, ((song.loudness or -20) + 60) / 60)),
    ]
    return np.array(audio + mfcc_13, dtype=np.float32)


# ── PyTorch Model ────────────────────────────────────────────────────────────
class SequentialLSTM(nn.Module):
    """2-layer LSTM that predicts the next song's feature embedding."""

    def __init__(self, input_dim=FEATURE_DIM, hidden_dim=HIDDEN_DIM,
                 num_layers=NUM_LAYERS, dropout=DROPOUT):
        super().__init__()
        self.lstm = nn.LSTM(
            input_dim, hidden_dim, num_layers,
            batch_first=True, dropout=dropout if num_layers > 1 else 0,
        )
        self.fc = nn.Sequential(
            nn.Linear(hidden_dim, hidden_dim),
            nn.ReLU(),
            nn.Dropout(dropout),
            nn.Linear(hidden_dim, input_dim),
        )

    def forward(self, x):
        # x: (batch, seq_len, feature_dim)
        lstm_out, _ = self.lstm(x)
        # Use the last hidden state to predict next embedding
        last_hidden = lstm_out[:, -1, :]
        return self.fc(last_hidden)


# ── Dataset ──────────────────────────────────────────────────────────────────
class SessionSequenceDataset(Dataset):
    """
    Builds (input_sequence, target_embedding) pairs from listening_history.
    Groups plays by session, orders by played_at, then creates sliding windows.
    """

    def __init__(self, sequences: list[np.ndarray], seq_length: int = SEQ_LENGTH):
        self.inputs = []
        self.targets = []

        for session_features in sequences:
            if len(session_features) < seq_length + 1:
                continue
            # Sliding window over the session
            for i in range(len(session_features) - seq_length):
                self.inputs.append(session_features[i:i + seq_length])
                self.targets.append(session_features[i + seq_length])

    def __len__(self):
        return len(self.inputs)

    def __getitem__(self, idx):
        return (
            torch.tensor(self.inputs[idx], dtype=torch.float32),
            torch.tensor(self.targets[idx], dtype=torch.float32),
        )


# ── Training ─────────────────────────────────────────────────────────────────
def _build_session_sequences(db) -> list[np.ndarray]:
    """
    Query listening_history, group by session_id, order by played_at,
    and convert each session to a sequence of feature vectors.
    """
    from sqlalchemy import func

    # Get sessions with enough songs
    session_counts = (
        db.query(ListeningHistory.session_id, func.count().label("cnt"))
        .filter(ListeningHistory.session_id.isnot(None))
        .group_by(ListeningHistory.session_id)
        .having(func.count() >= MIN_SEQ_LEN)
        .all()
    )

    if len(session_counts) < MIN_SESSIONS:
        logger.info(
            f"Only {len(session_counts)} sessions with {MIN_SEQ_LEN}+ songs "
            f"(need {MIN_SESSIONS}). Skipping LSTM training."
        )
        return []

    # Build feature sequences per session
    sequences = []
    for sc in session_counts:
        plays = (
            db.query(ListeningHistory)
            .filter(ListeningHistory.session_id == sc.session_id)
            .order_by(ListeningHistory.played_at.asc())
            .all()
        )

        # Load song objects for feature extraction
        song_ids = [p.song_id for p in plays]
        songs = {s.song_id: s for s in db.query(Song).filter(Song.song_id.in_(song_ids)).all()}

        features = []
        for p in plays:
            song = songs.get(p.song_id)
            if song and song.mfcc_vector:
                features.append(_song_to_features(song))

        if len(features) >= MIN_SEQ_LEN + 1:
            sequences.append(np.array(features))

    logger.info(f"Built {len(sequences)} session sequences for LSTM training")
    return sequences


def train_sequential() -> bool:
    """
    Train the LSTM sequential model on historical session data.
    Returns True if training succeeded, False if insufficient data.
    """
    db = SessionLocal()
    try:
        sequences = _build_session_sequences(db)
        if not sequences:
            return False

        # Fit a scaler on all features
        all_features = np.vstack(sequences)
        scaler = StandardScaler()
        scaler.fit(all_features)

        # Scale each sequence
        scaled_sequences = [scaler.transform(seq) for seq in sequences]

        # Build dataset
        dataset = SessionSequenceDataset(scaled_sequences, SEQ_LENGTH)
        if len(dataset) < 10:
            logger.info(f"Only {len(dataset)} training samples — skipping LSTM")
            return False

        dataloader = DataLoader(dataset, batch_size=BATCH_SIZE, shuffle=True)

        # Train
        device = torch.device("cpu")  # Keep on CPU for portability
        model = SequentialLSTM().to(device)
        optimizer = torch.optim.Adam(model.parameters(), lr=LR)
        criterion = nn.MSELoss()

        model.train()
        for epoch in range(EPOCHS):
            total_loss = 0.0
            for batch_x, batch_y in dataloader:
                batch_x, batch_y = batch_x.to(device), batch_y.to(device)
                optimizer.zero_grad()
                pred = model(batch_x)
                loss = criterion(pred, batch_y)
                loss.backward()
                optimizer.step()
                total_loss += loss.item()

            if (epoch + 1) % 10 == 0:
                avg_loss = total_loss / len(dataloader)
                logger.info(f"LSTM epoch {epoch+1}/{EPOCHS} — loss: {avg_loss:.6f}")

        # Save model + scaler
        MODEL_PATH.parent.mkdir(parents=True, exist_ok=True)
        torch.save(model.state_dict(), MODEL_PATH)
        with open(SCALER_PATH, "wb") as f:
            pickle.dump(scaler, f)

        logger.info(f"✅ LSTM model saved ({len(dataset)} samples, {EPOCHS} epochs)")
        return True

    except Exception as e:
        logger.error(f"LSTM training failed: {e}", exc_info=True)
        return False
    finally:
        db.close()


# ── Inference ────────────────────────────────────────────────────────────────
def predict_next_songs(
    recent_song_ids: list[str],
    top_n: int = 20,
) -> list[dict]:
    """
    Given a list of recently played song_ids, predict the next best songs.
    Returns list of {song_id, title, artist, genre, score} dicts.
    Returns empty list if model doesn't exist or input is insufficient.
    """
    if not MODEL_PATH.exists() or not SCALER_PATH.exists():
        return []

    if len(recent_song_ids) < SEQ_LENGTH:
        return []

    db = SessionLocal()
    try:
        # Load model + scaler
        with open(SCALER_PATH, "rb") as f:
            scaler = pickle.load(f)

        model = SequentialLSTM()
        model.load_state_dict(torch.load(MODEL_PATH, map_location="cpu", weights_only=True))
        model.eval()

        # Get feature vectors for recent songs
        recent_songs = db.query(Song).filter(Song.song_id.in_(recent_song_ids)).all()
        song_map = {s.song_id: s for s in recent_songs}

        # Build input sequence (last SEQ_LENGTH songs in order)
        features = []
        for sid in recent_song_ids[-SEQ_LENGTH:]:
            song = song_map.get(sid)
            if song and song.mfcc_vector:
                features.append(_song_to_features(song))

        if len(features) < SEQ_LENGTH:
            return []

        # Scale and predict
        seq = scaler.transform(np.array(features))
        input_tensor = torch.tensor(seq, dtype=torch.float32).unsqueeze(0)

        with torch.no_grad():
            predicted_embedding = model(input_tensor).numpy()[0]

        # Match against all library songs
        all_songs = db.query(Song).filter(
            Song.source.in_(["local", "ytmusic_only"]),
            Song.mfcc_vector.isnot(None),
        ).all()

        if not all_songs:
            return []

        library_features = np.array([_song_to_features(s) for s in all_songs])
        library_scaled = scaler.transform(library_features)

        similarities = cosine_similarity(
            predicted_embedding.reshape(1, -1),
            library_scaled,
        )[0]

        # Rank + exclude recently played
        recent_set = set(recent_song_ids)
        results = []
        for i, score in enumerate(similarities):
            song = all_songs[i]
            if song.song_id in recent_set:
                continue
            results.append({
                "song_id": song.song_id,
                "title":   song.title,
                "artist":  song.artist,
                "genre":   song.genre,
                "score":   round(float(score), 6),
            })

        results.sort(key=lambda x: x["score"], reverse=True)
        return results[:top_n]

    except Exception as e:
        logger.error(f"LSTM prediction failed: {e}", exc_info=True)
        return []
    finally:
        db.close()
