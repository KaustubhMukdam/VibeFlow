"""
app/models/genre/clustering.py
KMeans clustering to auto-discover genre-like groups from audio features.

This is the "zero-label" first step — no manual annotation required.
The resulting cluster_id is stored on each Song row.
A separate labeling step lets the user name each cluster.
"""
from __future__ import annotations

from pathlib import Path

import joblib
import numpy as np
import structlog
from sklearn.cluster import KMeans
from sklearn.decomposition import PCA
from sklearn.metrics import silhouette_score

from app.core.config import get_settings
from app.db.repository import SongRepo
from app.db.session import AsyncSession

log = structlog.get_logger(__name__)

KMEANS_PATH = Path("models_artifacts/genre_kmeans_v1.joblib")


def _fit_kmeans(X: np.ndarray, n_clusters: int) -> KMeans:
    """
    Fit KMeans with multiple random restarts (n_init=20) for stability.
    Uses the k-means++ initialisation strategy.
    """
    log.info("clustering.fitting", n_clusters=n_clusters, n_samples=X.shape[0])
    km = KMeans(
        n_clusters=n_clusters,
        init="k-means++",
        n_init=20,
        max_iter=500,
        random_state=42,
    )
    km.fit(X)
    score = silhouette_score(X, km.labels_, sample_size=min(500, X.shape[0]), random_state=42)
    log.info("clustering.done", inertia=round(km.inertia_, 2), silhouette=round(float(score), 4))
    return km


async def run_kmeans_clustering(
    db: AsyncSession,
    X: np.ndarray,
    song_ids: list[int],
    n_clusters: int | None = None,
    force_retrain: bool = False,
) -> np.ndarray:
    """
    Fit or load KMeans, assign cluster labels, and persist them to the DB.

    Returns:
        labels: np.ndarray of shape (n_songs,) with cluster assignments.
    """
    settings = get_settings()
    n_clusters = n_clusters or settings.N_GENRE_CLUSTERS

    if KMEANS_PATH.exists() and not force_retrain:
        log.info("clustering.loading_artifact", path=str(KMEANS_PATH))
        km: KMeans = joblib.load(KMEANS_PATH)
        labels = km.predict(X)
    else:
        km = _fit_kmeans(X, n_clusters)
        KMEANS_PATH.parent.mkdir(parents=True, exist_ok=True)
        joblib.dump(km, KMEANS_PATH)
        log.info("clustering.artifact_saved", path=str(KMEANS_PATH))
        labels = km.labels_

    # Write cluster_id back to each Song row
    for idx, (song_id, cluster_id) in enumerate(zip(song_ids, labels)):
        await SongRepo.update_genre(
            db,
            song_id=song_id,
            genre=f"cluster_{int(cluster_id)}",
            cluster_id=int(cluster_id),
        )

    log.info("clustering.db_updated", songs=len(song_ids))
    return labels


def get_cluster_distribution(labels: np.ndarray) -> dict[int, int]:
    """Return {cluster_id: count} dict for display."""
    unique, counts = np.unique(labels, return_counts=True)
    return {int(k): int(v) for k, v in zip(unique, counts)}
