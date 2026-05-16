"""
app/models/genre/classifier.py
Random Forest genre classifier — trained on labeled clusters.

Workflow:
  1. User runs clustering (KMeans assigns cluster_0 … cluster_11).
  2. User runs `python -m app.cli label` to rename clusters → actual genres.
  3. This module trains a RF on songs with confirmed genre labels.
  4. At inference time, it predicts genre + confidence for unlabeled songs.

The trained pipeline (StandardScaler + RandomForestClassifier) is saved as
a joblib artifact and loaded on API startup.
"""
from __future__ import annotations

from pathlib import Path
from typing import Optional

import joblib
import numpy as np
import structlog
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import classification_report
from sklearn.model_selection import StratifiedKFold, cross_val_score
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import LabelEncoder, StandardScaler

from app.db.repository import SongRepo
from app.db.session import AsyncSession

log = structlog.get_logger(__name__)

RF_PIPELINE_PATH = Path("models_artifacts/genre_rf_v1.joblib")
LABEL_ENCODER_PATH = Path("models_artifacts/genre_label_encoder_v1.joblib")


def _build_pipeline() -> Pipeline:
    return Pipeline([
        ("scaler", StandardScaler()),
        ("clf", RandomForestClassifier(
            n_estimators=300,
            max_depth=None,
            min_samples_leaf=2,
            class_weight="balanced",
            random_state=42,
            n_jobs=-1,
        )),
    ])


def train_genre_classifier(
    X: np.ndarray,
    y_labels: list[str],
    run_cv: bool = True,
) -> tuple[Pipeline, LabelEncoder, dict]:
    """
    Train the Random Forest classifier.

    Args:
        X: Feature matrix (n_samples, n_features) — NOT pre-scaled
           (the Pipeline includes a StandardScaler step).
        y_labels: String genre labels for each row in X.
        run_cv: If True, run 5-fold stratified CV and include scores in metrics.

    Returns:
        pipeline: Fitted sklearn Pipeline.
        le: Fitted LabelEncoder mapping genre strings ↔ integers.
        metrics: Dict of training metrics.
    """
    le = LabelEncoder()
    y = le.fit_transform(y_labels)

    pipeline = _build_pipeline()

    metrics: dict = {"n_samples": len(y), "classes": list(le.classes_)}

    if run_cv and len(np.unique(y)) > 1:
        cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)
        cv_scores = cross_val_score(pipeline, X, y, cv=cv, scoring="f1_weighted")
        metrics["cv_f1_mean"] = round(float(cv_scores.mean()), 4)
        metrics["cv_f1_std"] = round(float(cv_scores.std()), 4)
        log.info("classifier.cv_done", **{k: v for k, v in metrics.items() if "cv" in k})

    pipeline.fit(X, y)

    y_pred = pipeline.predict(X)
    report = classification_report(y, y_pred, target_names=le.classes_, output_dict=True)
    metrics["train_accuracy"] = round(float(report.get("accuracy", 0)), 4)

    RF_PIPELINE_PATH.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(pipeline, RF_PIPELINE_PATH)
    joblib.dump(le, LABEL_ENCODER_PATH)

    log.info("classifier.trained", **{k: v for k, v in metrics.items() if k != "classes"})
    return pipeline, le, metrics


async def predict_genres_batch(
    song_ids: list[int],
    X: np.ndarray,
    db: AsyncSession,
) -> dict[int, tuple[str, float]]:
    """
    Batch inference: predict genre + confidence for each song.
    Updates the predicted_genre and genre_confidence columns in the DB.

    Returns:
        dict mapping song_id → (predicted_genre, confidence)
    """
    if not RF_PIPELINE_PATH.exists():
        log.warning("classifier.no_artifact_found")
        return {}

    pipeline: Pipeline = joblib.load(RF_PIPELINE_PATH)
    le: LabelEncoder = joblib.load(LABEL_ENCODER_PATH)

    proba = pipeline.predict_proba(X)  # (n, n_classes)
    predicted_idx = np.argmax(proba, axis=1)
    confidences = proba[np.arange(len(proba)), predicted_idx]

    results: dict[int, tuple[str, float]] = {}

    for i, (song_id, pred_idx, conf) in enumerate(zip(song_ids, predicted_idx, confidences)):
        genre = le.classes_[pred_idx]
        confidence = float(conf)
        results[song_id] = (genre, confidence)
        await SongRepo.update_genre(db, song_id=song_id, genre=genre, confidence=confidence)

    log.info("classifier.batch_predicted", count=len(results))
    return results


def load_artifacts() -> Optional[tuple[Pipeline, LabelEncoder]]:
    """Load persisted pipeline + label encoder. Returns None if not trained yet."""
    if RF_PIPELINE_PATH.exists() and LABEL_ENCODER_PATH.exists():
        return joblib.load(RF_PIPELINE_PATH), joblib.load(LABEL_ENCODER_PATH)
    return None
