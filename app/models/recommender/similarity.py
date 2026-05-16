"""
app/models/recommender/similarity.py
Content-based similarity engine using cosine similarity on audio feature vectors.

The full similarity matrix is precomputed once and cached in memory.
For 600 songs, the matrix is 600×600 = 360,000 float32 values ≈ 1.4 MB — trivial.
"""
from __future__ import annotations

import numpy as np
import structlog
from sklearn.metrics.pairwise import cosine_similarity

log = structlog.get_logger(__name__)

# Module-level cache
_similarity_matrix: np.ndarray | None = None
_cached_song_ids: list[int] | None = None


def build_similarity_matrix(X: np.ndarray, song_ids: list[int]) -> np.ndarray:
    """
    Compute and cache the full cosine similarity matrix.

    Args:
        X:        (n_songs, n_features) normalised feature matrix.
        song_ids: list of song IDs in the same row order as X.

    Returns:
        sim_matrix: (n_songs, n_songs) float32 matrix.
    """
    global _similarity_matrix, _cached_song_ids
    log.info("similarity.building_matrix", n_songs=X.shape[0])
    sim = cosine_similarity(X).astype(np.float32)
    np.fill_diagonal(sim, 0.0)  # a song is not similar to itself
    _similarity_matrix = sim
    _cached_song_ids = list(song_ids)
    log.info("similarity.matrix_ready", shape=sim.shape)
    return sim


def get_similar_songs(
    song_id: int,
    top_k: int = 20,
) -> list[tuple[int, float]]:
    """
    Return the top-k most acoustically similar songs to `song_id`.

    Returns:
        list of (similar_song_id, similarity_score) sorted descending.
    """
    if _similarity_matrix is None or _cached_song_ids is None:
        raise RuntimeError("Similarity matrix not built. Call build_similarity_matrix first.")

    if song_id not in _cached_song_ids:
        log.warning("similarity.song_not_in_matrix", song_id=song_id)
        return []

    idx = _cached_song_ids.index(song_id)
    scores = _similarity_matrix[idx]  # (n_songs,)

    # Get top-k indices
    top_indices = np.argsort(scores)[::-1][:top_k]
    return [
        (_cached_song_ids[i], float(scores[i]))
        for i in top_indices
        if scores[i] > 0
    ]


def get_similar_to_many(
    song_ids: list[int],
    top_k: int = 30,
    exclude_ids: set[int] | None = None,
) -> list[tuple[int, float]]:
    """
    Aggregate similarity scores across multiple seed songs.
    Useful for 'more like songs I liked recently'.
    """
    if not song_ids:
        return []

    exclude = exclude_ids or set()
    score_accumulator: dict[int, float] = {}

    for seed_id in song_ids:
        for similar_id, score in get_similar_songs(seed_id, top_k=top_k * 2):
            if similar_id not in exclude and similar_id not in song_ids:
                score_accumulator[similar_id] = score_accumulator.get(similar_id, 0.0) + score

    sorted_results = sorted(score_accumulator.items(), key=lambda x: x[1], reverse=True)
    return sorted_results[:top_k]


def is_matrix_ready() -> bool:
    return _similarity_matrix is not None
