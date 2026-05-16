"""
app/features/extractor.py
Librosa-based audio feature extraction for a single track.

Features extracted:
  - MFCC: 40 coefficients → mean + std (80 floats)
  - Chroma STFT: 12 pitch classes → mean + std (24 floats)
  - Tempo (float)
  - Spectral Centroid → mean + std
  - Zero Crossing Rate → mean + std
  - Spectral Rolloff → mean
  - RMS Energy → mean
  - Estimated key (0–11) and mode (0=minor, 1=major)

Designed to be called from a ThreadPoolExecutor (CPU-bound) or
from a Vertex AI Workbench notebook.
"""
from __future__ import annotations

import json
import warnings
from pathlib import Path
from typing import Optional

import numpy as np
import structlog

# Suppress librosa's numba cache warnings in production
warnings.filterwarnings("ignore", category=UserWarning, module="librosa")

log = structlog.get_logger(__name__)

# We import librosa lazily at module level — it's always available since it's
# installed, but this avoids import cost at CLI startup.
try:
    import librosa
    LIBROSA_AVAILABLE = True
except ImportError:
    LIBROSA_AVAILABLE = False
    log.error("features.librosa_not_installed")


# ─── Output model (plain dataclass for speed) ─────────────────────────────────

class AudioFeatureVector:
    """
    Container for all extracted features.
    JSON-serialised list fields match the AudioFeature ORM model.
    """
    __slots__ = (
        "song_id",
        "mfcc_mean", "mfcc_std",
        "chroma_mean", "chroma_std",
        "tempo",
        "spectral_centroid_mean", "spectral_centroid_std",
        "zcr_mean", "zcr_std",
        "spectral_rolloff_mean",
        "rms_mean",
        "estimated_key", "estimated_mode",
    )

    def __init__(self, song_id: int, **kwargs):
        self.song_id = song_id
        for k in self.__slots__[1:]:
            setattr(self, k, kwargs.get(k))

    def to_orm_kwargs(self) -> dict:
        """Return a dict suitable for constructing an AudioFeature ORM instance."""
        return {
            "song_id": self.song_id,
            "mfcc_mean": json.dumps([round(float(x), 6) for x in self.mfcc_mean]) if self.mfcc_mean is not None else None,
            "mfcc_std": json.dumps([round(float(x), 6) for x in self.mfcc_std]) if self.mfcc_std is not None else None,
            "chroma_mean": json.dumps([round(float(x), 6) for x in self.chroma_mean]) if self.chroma_mean is not None else None,
            "chroma_std": json.dumps([round(float(x), 6) for x in self.chroma_std]) if self.chroma_std is not None else None,
            "tempo": float(self.tempo) if self.tempo is not None else None,
            "spectral_centroid_mean": float(self.spectral_centroid_mean) if self.spectral_centroid_mean is not None else None,
            "spectral_centroid_std": float(self.spectral_centroid_std) if self.spectral_centroid_std is not None else None,
            "zcr_mean": float(self.zcr_mean) if self.zcr_mean is not None else None,
            "zcr_std": float(self.zcr_std) if self.zcr_std is not None else None,
            "spectral_rolloff_mean": float(self.spectral_rolloff_mean) if self.spectral_rolloff_mean is not None else None,
            "rms_mean": float(self.rms_mean) if self.rms_mean is not None else None,
            "estimated_key": int(self.estimated_key) if self.estimated_key is not None else None,
            "estimated_mode": int(self.estimated_mode) if self.estimated_mode is not None else None,
        }


# ─── Key/Mode estimation ──────────────────────────────────────────────────────

# Krumhansl-Kessler key profiles
_MAJOR_PROFILE = np.array([6.35, 2.23, 3.48, 2.33, 4.38, 4.09, 2.52, 5.19, 2.39, 3.66, 2.29, 2.88])
_MINOR_PROFILE = np.array([6.33, 2.68, 3.52, 5.38, 2.60, 3.53, 2.54, 4.75, 3.98, 2.69, 3.34, 3.17])


def _estimate_key_mode(chroma_mean: np.ndarray) -> tuple[int, int]:
    """
    Estimate musical key (0=C … 11=B) and mode (0=minor, 1=major)
    using correlation with Krumhansl-Kessler profiles.
    """
    best_corr = -np.inf
    best_key = 0
    best_mode = 1

    for key in range(12):
        rotated_chroma = np.roll(chroma_mean, -key)
        major_corr = float(np.corrcoef(rotated_chroma, _MAJOR_PROFILE)[0, 1])
        minor_corr = float(np.corrcoef(rotated_chroma, _MINOR_PROFILE)[0, 1])
        if major_corr > best_corr:
            best_corr = major_corr
            best_key = key
            best_mode = 1
        if minor_corr > best_corr:
            best_corr = minor_corr
            best_key = key
            best_mode = 0

    return best_key, best_mode


# ─── Main extraction function ─────────────────────────────────────────────────

def extract_features(
    file_path: Path,
    song_id: int,
    sr: int = 22050,
    duration: Optional[float] = 30.0,
    n_mfcc: int = 40,
) -> Optional[AudioFeatureVector]:
    """
    Extract audio features from a single file using librosa.

    Args:
        file_path:  Path to the audio file.
        song_id:    DB primary key to embed in the result.
        sr:         Target sample rate (22050 Hz is librosa's default).
        duration:   Seconds to analyse. None = full track. 30s is the sweet spot
                    between accuracy and speed for genre classification.
        n_mfcc:     Number of MFCC coefficients.

    Returns:
        AudioFeatureVector on success, None on failure (corrupt / unsupported file).
    """
    if not LIBROSA_AVAILABLE:
        raise RuntimeError("librosa is not installed")

    path = Path(file_path)
    if not path.exists():
        log.warning("extractor.file_not_found", path=str(path))
        return None

    try:
        # Load audio — librosa handles MP3, FLAC, OGG, WAV natively.
        # M4A requires audioread (bundled with librosa on most installs).
        y, sr_loaded = librosa.load(str(path), sr=sr, mono=True, duration=duration)

        if len(y) < sr * 1:  # skip files shorter than 1 second
            log.warning("extractor.too_short", path=str(path), length_sec=len(y)/sr)
            return None

        # ── MFCCs ─────────────────────────────────────────────────────────────
        mfccs = librosa.feature.mfcc(y=y, sr=sr_loaded, n_mfcc=n_mfcc)
        mfcc_mean = np.mean(mfccs, axis=1)
        mfcc_std = np.std(mfccs, axis=1)

        # ── Chroma ────────────────────────────────────────────────────────────
        chroma = librosa.feature.chroma_stft(y=y, sr=sr_loaded)
        chroma_mean = np.mean(chroma, axis=1)
        chroma_std = np.std(chroma, axis=1)

        # ── Tempo ─────────────────────────────────────────────────────────────
        tempo, _ = librosa.beat.beat_track(y=y, sr=sr_loaded)
        tempo_val = float(tempo) if np.isscalar(tempo) else float(tempo[0])

        # ── Spectral Centroid ─────────────────────────────────────────────────
        spec_centroid = librosa.feature.spectral_centroid(y=y, sr=sr_loaded)
        sc_mean = float(np.mean(spec_centroid))
        sc_std = float(np.std(spec_centroid))

        # ── Zero Crossing Rate ────────────────────────────────────────────────
        zcr = librosa.feature.zero_crossing_rate(y)
        zcr_mean = float(np.mean(zcr))
        zcr_std = float(np.std(zcr))

        # ── Spectral Rolloff ──────────────────────────────────────────────────
        rolloff = librosa.feature.spectral_rolloff(y=y, sr=sr_loaded)
        rolloff_mean = float(np.mean(rolloff))

        # ── RMS Energy ────────────────────────────────────────────────────────
        rms = librosa.feature.rms(y=y)
        rms_mean = float(np.mean(rms))

        # ── Key / Mode ────────────────────────────────────────────────────────
        estimated_key, estimated_mode = _estimate_key_mode(chroma_mean)

        return AudioFeatureVector(
            song_id=song_id,
            mfcc_mean=mfcc_mean,
            mfcc_std=mfcc_std,
            chroma_mean=chroma_mean,
            chroma_std=chroma_std,
            tempo=tempo_val,
            spectral_centroid_mean=sc_mean,
            spectral_centroid_std=sc_std,
            zcr_mean=zcr_mean,
            zcr_std=zcr_std,
            spectral_rolloff_mean=rolloff_mean,
            rms_mean=rms_mean,
            estimated_key=estimated_key,
            estimated_mode=estimated_mode,
        )

    except Exception as exc:
        log.warning("extractor.failed", path=str(path), error=str(exc))
        return None
