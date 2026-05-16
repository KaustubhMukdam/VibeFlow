"""
app/features/feature_matrix.py
Builds a normalised NumPy feature matrix from all AudioFeature rows in the DB.
Used by the genre clustering and similarity engine.

The feature vector for each song is:
  mfcc_mean (40) + mfcc_std (40) + chroma_mean (12) + chroma_std (12)
  + [tempo, spectral_centroid_mean, spectral_centroid_std,
     zcr_mean, zcr_std, spectral_rolloff_mean, rms_mean]  (7 scalars)
= 111 dimensions total

The StandardScaler is persisted as a joblib artifact so inference uses
the same normalisation as training.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

import joblib
import numpy as np
import structlog
from sklearn.preprocessing import StandardScaler

from app.db.models import AudioFeature
from app.db.repository import FeatureRepo
from app.db.session import AsyncSession

log = structlog.get_logger(__name__)

SCALER_PATH = Path("models_artifacts/feature_scaler.joblib")


def _feature_row(af: AudioFeature) -> Optional[np.ndarray]:
    """Build a single flat feature vector from an AudioFeature ORM row."""
    try:
        mfcc_mean = af.get_mfcc_mean()
        mfcc_std = af.get_mfcc_std()
        chroma_mean = af.get_chroma_mean()
        chroma_std = af.get_chroma_std()

        # Guard against incomplete rows
        if not mfcc_mean or not chroma_mean:
            return None

        scalars = [
            af.tempo or 0.0,
            af.spectral_centroid_mean or 0.0,
            af.spectral_centroid_std or 0.0,
            af.zcr_mean or 0.0,
            af.zcr_std or 0.0,
            af.spectral_rolloff_mean or 0.0,
            af.rms_mean or 0.0,
        ]

        return np.array(mfcc_mean + mfcc_std + chroma_mean + chroma_std + scalars, dtype=np.float32)
    except Exception as exc:
        log.warning("feature_matrix.row_error", song_id=af.song_id, error=str(exc))
        return None


async def build_feature_matrix(
    db: AsyncSession,
    fit_scaler: bool = False,
) -> tuple[np.ndarray, list[int]]:
    """
    Load all AudioFeature rows and return:
      - X: (n_songs, 111) normalised float32 matrix
      - song_ids: list[int] mapping row index → song DB id

    Args:
        fit_scaler: If True, fit a new StandardScaler and save it.
                    If False, load the existing scaler (for inference).
    """
    features = await FeatureRepo.get_all(db)
    log.info("feature_matrix.loading", count=len(features))

    rows: list[np.ndarray] = []
    ids: list[int] = []

    for af in features:
        row = _feature_row(af)
        if row is not None:
            rows.append(row)
            ids.append(af.song_id)

    if not rows:
        raise ValueError("No features found in DB. Run feature extraction first.")

    X_raw = np.vstack(rows)  # (n, 111)
    log.info("feature_matrix.built", shape=X_raw.shape)

    if fit_scaler or not SCALER_PATH.exists():
        scaler = StandardScaler()
        X = scaler.fit_transform(X_raw).astype(np.float32)
        SCALER_PATH.parent.mkdir(parents=True, exist_ok=True)
        joblib.dump(scaler, SCALER_PATH)
        log.info("feature_matrix.scaler_saved", path=str(SCALER_PATH))
    else:
        scaler: StandardScaler = joblib.load(SCALER_PATH)
        X = scaler.transform(X_raw).astype(np.float32)
        log.info("feature_matrix.scaler_loaded", path=str(SCALER_PATH))

    return X, ids
