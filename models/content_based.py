import logging
import numpy as np
import pandas as pd
from sklearn.preprocessing import StandardScaler
from sklearn.metrics.pairwise import cosine_similarity
from typing import Optional
from db import SessionLocal
from db.models import Song

logger = logging.getLogger(__name__)

AUDIO_FEATURES = [
    "energy", "tempo", "acousticness",
    "instrumentalness", "speechiness", "loudness",
]
MFCC_WEIGHT = 2.0   # MFCCs carry more genre signal — upweight them


def _load_feature_matrix(db) -> tuple[pd.DataFrame, np.ndarray]:
    """
    Load all songs with features from DB.
    Returns (metadata_df, scaled_feature_matrix).
    """
    songs = db.query(Song).filter(
        Song.source.in_(["local", "ytmusic_only"]),
        Song.mfcc_vector.isnot(None),
    ).all()

    if not songs:
        raise ValueError("No songs with features found in DB. Run ingestion first.")

    rows = []
    for s in songs:
        mfcc = s.mfcc_vector if isinstance(s.mfcc_vector, list) else []
        row = {
            "song_id": s.song_id,
            "title":   s.title,
            "artist":  s.artist,
            "genre":   s.genre,
        }
        for feat in AUDIO_FEATURES:
            row[feat] = getattr(s, feat) or 0.0
        for i, val in enumerate(mfcc):
            row[f"mfcc_{i}"] = val * MFCC_WEIGHT
        rows.append(row)

    df = pd.DataFrame(rows).set_index("song_id")
    meta_cols = ["title", "artist", "genre"]
    feat_cols = [c for c in df.columns if c not in meta_cols]

    X = df[feat_cols].fillna(0.0).values
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)

    return df[meta_cols], X_scaled, df.index.tolist()


def get_similar_songs(
    song_id: str,
    top_n: int = 20,
    same_genre_boost: float = 0.1,
) -> list[dict]:
    """
    Find top_n songs most similar to the given song_id using cosine similarity.
    Applies a small boost for songs in the same genre bucket.
    Returns list of {song_id, title, artist, genre, score} dicts.
    """
    db = SessionLocal()
    try:
        meta_df, X_scaled, song_ids = _load_feature_matrix(db)

        if song_id not in song_ids:
            logger.warning(f"song_id '{song_id}' not found in feature matrix")
            return []

        idx = song_ids.index(song_id)
        query_vec = X_scaled[idx].reshape(1, -1)
        sims = cosine_similarity(query_vec, X_scaled)[0]

        query_genre = meta_df.loc[song_id, "genre"] if song_id in meta_df.index else None

        results = []
        for i, score in enumerate(sims):
            sid = song_ids[i]
            if sid == song_id:
                continue
            genre = meta_df.loc[sid, "genre"] if sid in meta_df.index else None
            if query_genre and genre == query_genre:
                score += same_genre_boost   # Reward same-genre matches
            results.append({
                "song_id": sid,
                "title":   meta_df.loc[sid, "title"],
                "artist":  meta_df.loc[sid, "artist"],
                "genre":   genre,
                "score":   round(float(score), 6),
            })

        results.sort(key=lambda x: x["score"], reverse=True)
        return results[:top_n]

    finally:
        db.close()


def get_recommendations_for_user(
    top_n: int = 50,
    seed_song_ids: Optional[list[str]] = None,
) -> list[dict]:
    """
    Generate recommendations based on seed songs.
    Cold-start fallback: if no seeds exist, seeds from genre-diverse
    high-confidence songs in the library itself.
    """
    db = SessionLocal()
    try:
        meta_df, X_scaled, song_ids = _load_feature_matrix(db)

        # ── Cold-start: no history at all ────────────────────────────────
        if not seed_song_ids:
            from db.models import ListeningHistory
            from sqlalchemy import func
            top_played = (
                db.query(ListeningHistory.song_id)
                .group_by(ListeningHistory.song_id)
                .order_by(func.count().desc())
                .limit(20)
                .all()
            )
            seed_song_ids = [r.song_id for r in top_played]

        if not seed_song_ids:
            # True cold-start — pick one high-confidence song per genre as seeds
            logger.info("Cold-start mode: seeding from genre-diverse library sample")
            seed_song_ids = _cold_start_seeds(db)

        if not seed_song_ids:
            logger.warning("Library is empty — cannot generate recommendations")
            return []

        valid_seeds = [s for s in seed_song_ids if s in song_ids]
        if not valid_seeds:
            return []

        agg_scores = np.zeros(len(song_ids))
        for seed_id in valid_seeds:
            idx = song_ids.index(seed_id)
            query_vec = X_scaled[idx].reshape(1, -1)
            sims = cosine_similarity(query_vec, X_scaled)[0]
            agg_scores += sims

        agg_scores /= len(valid_seeds)

        results = []
        for i, score in enumerate(agg_scores):
            sid = song_ids[i]
            if sid in seed_song_ids:
                continue
            results.append({
                "song_id": sid,
                "title":   meta_df.loc[sid, "title"] if sid in meta_df.index else "Unknown",
                "artist":  meta_df.loc[sid, "artist"] if sid in meta_df.index else "Unknown",
                "genre":   meta_df.loc[sid, "genre"] if sid in meta_df.index else None,
                "score":   round(float(score), 6),
            })

        results.sort(key=lambda x: x["score"], reverse=True)
        return results[:top_n]

    finally:
        db.close()


def _cold_start_seeds(db, songs_per_genre: int = 5) -> list[str]:
    """
    Pick the top N highest-confidence songs per genre as cold-start seeds.
    Ensures genre diversity when no listening history exists.
    """
    from db.models import Song
    seeds = []
    genres = db.query(Song.genre).filter(
        Song.source == "local",
        Song.genre.isnot(None),
    ).distinct().all()

    for (genre,) in genres:
        top_songs = (
            db.query(Song.song_id)
            .filter(
                Song.source == "local",
                Song.genre == genre,
                Song.genre_confidence.isnot(None),
            )
            .order_by(Song.genre_confidence.desc())
            .limit(songs_per_genre)
            .all()
        )
        seeds.extend([s.song_id for s in top_songs])

    logger.info(f"Cold-start seeds: {len(seeds)} songs across {len(genres)} genres")
    return seeds
