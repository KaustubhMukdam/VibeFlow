import logging
import pickle
import numpy as np
import scipy.sparse as sp
from pathlib import Path
from typing import Optional
from implicit.als import AlternatingLeastSquares
from db import SessionLocal
from db.models import ListeningHistory, Song

logger = logging.getLogger(__name__)

SAVED_DIR = Path("models/genre_classifier/saved")   # reuse saved dir
ALS_MODEL_PATH = Path("models/saved/als_model.pkl")
ALS_MAPPINGS_PATH = Path("models/saved/als_mappings.pkl")

MIN_INTERACTIONS = 10   # Minimum history records to train ALS


def _build_interaction_matrix(db) -> tuple:
    """
    Build a user×song implicit feedback matrix from listening_history.

    Since VibeFlow is single-user, 'user' = 0 (one row).
    Confidence weight = f(completion_pct, skip):
      - Full play (≥80%): weight 2.0
      - Partial (40–80%): weight 1.0
      - Short play (15–40%): weight 0.5
      - Skip (<15% or skipped=True): weight 0.1
    """
    history = db.query(ListeningHistory).all()
    if len(history) < MIN_INTERACTIONS:
        return None, None, None

    songs = db.query(Song.song_id).filter(
        Song.source.in_(["local", "ytmusic_only"])
    ).all()
    song_ids = [s.song_id for s in songs]
    song_to_idx = {sid: i for i, sid in enumerate(song_ids)}

    n_songs = len(song_ids)
    weights = {}

    for record in history:
        sid = record.song_id
        if sid not in song_to_idx:
            continue
        idx = song_to_idx[sid]

        if record.skipped:
            w = 0.1
        elif record.play_duration_ms and record.song_duration_ms and record.song_duration_ms > 0:
            pct = (record.play_duration_ms / record.song_duration_ms) * 100
            if pct >= 80:
                w = 2.0
            elif pct >= 40:
                w = 1.0
            elif pct >= 15:
                w = 0.5
            else:
                w = 0.1
        else:
            w = 1.0   # Unknown completion — assume played

        weights[idx] = weights.get(idx, 0) + w

    if not weights:
        return None, None, None

    rows = [0] * len(weights)   # Single user
    cols = list(weights.keys())
    data = list(weights.values())

    matrix = sp.csr_matrix((data, (rows, cols)), shape=(1, n_songs))
    return matrix, song_ids, song_to_idx


def train_als(factors: int = 64, iterations: int = 20, regularization: float = 0.1):
    """Train ALS model on listening history. Saves model + mappings."""
    db = SessionLocal()
    try:
        matrix, song_ids, song_to_idx = _build_interaction_matrix(db)

        if matrix is None:
            logger.warning(
                f"Not enough interaction data for ALS "
                f"(need ≥{MIN_INTERACTIONS} records). "
                f"Using content-based only."
            )
            return None

        logger.info(f"Training ALS on {matrix.nnz} interactions across {len(song_ids)} songs...")

        model = AlternatingLeastSquares(
            factors=factors,
            iterations=iterations,
            regularization=regularization,
            use_gpu=False,
            calculate_training_loss=True,
            random_state=42,
        )
        
        # FIX: Pass 'matrix' directly (user x item) instead of transposing it.
        model.fit(matrix, show_progress=True)

        Path("models/saved").mkdir(parents=True, exist_ok=True)
        with open(ALS_MODEL_PATH, "wb") as f:
            pickle.dump(model, f)
        with open(ALS_MAPPINGS_PATH, "wb") as f:
            pickle.dump({"song_ids": song_ids, "song_to_idx": song_to_idx}, f)

        logger.info(f"ALS model saved — {len(song_ids)} items, {matrix.nnz} interactions")
        return model

    finally:
        db.close()


def get_als_recommendations(top_n: int = 50) -> list[dict]:
    """
    Get ALS-based recommendations for the single user.
    Falls back to empty list if model not trained yet.
    """
    if not ALS_MODEL_PATH.exists() or not ALS_MAPPINGS_PATH.exists():
        logger.info("ALS model not found — skipping collaborative filtering")
        return []

    db = SessionLocal()
    try:
        with open(ALS_MODEL_PATH, "rb") as f:
            model = pickle.load(f)
        with open(ALS_MAPPINGS_PATH, "rb") as f:
            mappings = pickle.load(f)

        song_ids = mappings["song_ids"]
        song_to_idx = mappings["song_to_idx"]

        matrix, _, _ = _build_interaction_matrix(db)
        if matrix is None:
            return []

        # FIX: Ensure we don't request more items than the model was trained on
        safe_top_n = min(top_n + 20, len(song_ids))
        if safe_top_n <= 0:
            return []

        # Recommend for user 0
        item_ids, scores = model.recommend(
            0,
            matrix,
            N=safe_top_n, 
            filter_already_liked_items=True,
        )

        results = []
        for item_idx, score in zip(item_ids, scores):
            if item_idx >= len(song_ids):
                continue
            sid = song_ids[item_idx]
            song = db.query(Song).filter_by(song_id=sid).first()
            if song:
                results.append({
                    "song_id": sid,
                    "title": song.title,
                    "artist": song.artist,
                    "genre": song.genre,
                    "score": round(float(score), 6),
                })
            if len(results) >= top_n:
                break

        return results

    finally:
        db.close()