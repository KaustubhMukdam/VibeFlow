"""
app/api/routes/models.py
ML model management endpoints — trigger training, check status.
"""
from __future__ import annotations

from pathlib import Path
from typing import Annotated

import structlog
from fastapi import APIRouter, BackgroundTasks, Depends
from pydantic import BaseModel

from app.db.repository import FeatureRepo, SongRepo
from app.db.session import AsyncSession, get_db
from app.features.feature_matrix import SCALER_PATH, build_feature_matrix
from app.features.pipeline import run_feature_extraction
from app.models.genre.classifier import RF_PIPELINE_PATH, train_genre_classifier
from app.models.genre.clustering import KMEANS_PATH, run_kmeans_clustering
from app.models.recommender.similarity import build_similarity_matrix, is_matrix_ready

router = APIRouter(prefix="/models", tags=["Models"])
log = structlog.get_logger(__name__)

_extraction_status: dict = {"running": False, "last_result": None}
_training_status: dict = {"running": False, "last_result": None}


# ─── Schemas ──────────────────────────────────────────────────────────────────

class ModelStatus(BaseModel):
    feature_scaler_ready: bool
    kmeans_ready: bool
    classifier_ready: bool
    similarity_matrix_ready: bool
    songs_with_features: int
    total_songs: int


class TrainingResult(BaseModel):
    status: str
    details: dict


# ─── Endpoints ────────────────────────────────────────────────────────────────

@router.get("/status", response_model=ModelStatus, summary="Model artifact status")
async def model_status(
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ModelStatus:
    return ModelStatus(
        feature_scaler_ready=SCALER_PATH.exists(),
        kmeans_ready=KMEANS_PATH.exists(),
        classifier_ready=RF_PIPELINE_PATH.exists(),
        similarity_matrix_ready=is_matrix_ready(),
        songs_with_features=await FeatureRepo.count_extracted(db),
        total_songs=await SongRepo.count(db),
    )


@router.post("/train/features", response_model=TrainingResult, summary="Run feature extraction")
async def trigger_feature_extraction(
    db: Annotated[AsyncSession, Depends(get_db)],
) -> TrainingResult:
    """
    Run audio feature extraction for all songs without features.
    This is synchronous for now — for very large libraries consider a background task.
    """
    if _extraction_status["running"]:
        return TrainingResult(status="already_running", details={})
    _extraction_status["running"] = True
    try:
        summary = await run_feature_extraction(db, show_progress=False)
        _extraction_status["last_result"] = summary
        return TrainingResult(status="complete", details=summary)
    finally:
        _extraction_status["running"] = False


@router.post("/train/genre", response_model=TrainingResult, summary="Run genre clustering + classification")
async def trigger_genre_training(
    db: Annotated[AsyncSession, Depends(get_db)],
    force_retrain: bool = False,
) -> TrainingResult:
    """
    Step 1: KMeans clustering assigns cluster_id to each song.
    Step 2: If genre labels exist, train the Random Forest classifier.
    Step 3: Rebuild the similarity matrix.
    """
    if _training_status["running"]:
        return TrainingResult(status="already_running", details={})
    _training_status["running"] = True
    try:
        X, song_ids = await build_feature_matrix(db, fit_scaler=True)
        labels = await run_kmeans_clustering(db, X, song_ids, force_retrain=force_retrain)

        # Attempt supervised training if genre labels exist
        songs = await SongRepo.get_all_active(db)
        labeled = [(s, X[song_ids.index(s.id)]) for s in songs
                   if s.predicted_genre and not s.predicted_genre.startswith("cluster_")
                   and s.id in song_ids]

        classifier_trained = False
        cv_f1 = None
        if len(labeled) >= 20:
            X_labeled = [row for _, row in labeled]
            y_labeled = [s.predicted_genre for s, _ in labeled]
            import numpy as np
            _, _, metrics = train_genre_classifier(np.array(X_labeled), y_labeled)
            classifier_trained = True
            cv_f1 = metrics.get("cv_f1_mean")

        # Rebuild similarity matrix
        build_similarity_matrix(X, song_ids)

        details = {
            "songs_clustered": len(song_ids),
            "n_clusters": int(max(labels) + 1),
            "classifier_trained": classifier_trained,
            "cv_f1_mean": cv_f1,
            "similarity_matrix_built": True,
        }
        _training_status["last_result"] = details
        return TrainingResult(status="complete", details=details)
    finally:
        _training_status["running"] = False
