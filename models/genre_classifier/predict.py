import pickle
import logging
import numpy as np
from pathlib import Path
from typing import Optional
from models.genre_classifier.train import extract_features_from_file, GENRE_MAP, SAVED_DIR

logger = logging.getLogger(__name__)

# Cache loaded artifacts in module scope — only loads once
_model   = None
_scaler  = None
_encoder = None


def _load_artifacts():
    global _model, _scaler, _encoder
    if _model is not None:
        return  # Already loaded

    required = ["xgb_genre_model.pkl", "scaler.pkl", "label_encoder.pkl"]
    for fname in required:
        if not (SAVED_DIR / fname).exists():
            raise FileNotFoundError(
                f"Model artifact not found: {SAVED_DIR / fname}\n"
                f"Run: python -m models.genre_classifier.train first."
            )

    with open(SAVED_DIR / "xgb_genre_model.pkl", "rb") as f:
        _model = pickle.load(f)
    with open(SAVED_DIR / "scaler.pkl", "rb") as f:
        _scaler = pickle.load(f)
    with open(SAVED_DIR / "label_encoder.pkl", "rb") as f:
        _encoder = pickle.load(f)

    logger.info("Genre classifier artifacts loaded")


def predict_genre(file_path: str) -> Optional[dict]:
    """
    Predict genre for a single audio file.
    Returns {gtzan_genre, vibeflow_genre, confidence} or None on failure.
    """
    _load_artifacts()

    features = extract_features_from_file(file_path)
    if features is None:
        return None

    features_scaled = _scaler.transform(features.reshape(1, -1))
    proba = _model.predict_proba(features_scaled)[0]
    pred_idx = int(np.argmax(proba))
    confidence = float(proba[pred_idx])
    gtzan_genre = _encoder.inverse_transform([pred_idx])[0]
    vibeflow_genre = GENRE_MAP.get(gtzan_genre, "Pop")

    return {
        "gtzan_genre":    gtzan_genre,
        "vibeflow_genre": vibeflow_genre,
        "confidence":     round(confidence, 4),
        "all_probs":      {
            cls: round(float(p), 4)
            for cls, p in zip(_encoder.classes_, proba)
        },
    }


def predict_batch(file_paths: list[str]) -> list[Optional[dict]]:
    """Predict genres for a list of files. Skips failed files gracefully."""
    _load_artifacts()
    results = []
    for idx, path in enumerate(file_paths):
        if idx % 50 == 0:
            logger.info(f"Genre prediction: [{idx}/{len(file_paths)}]")
        results.append(predict_genre(path))
    return results
