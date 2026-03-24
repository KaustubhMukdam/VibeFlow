import os
import pickle
import logging
import numpy as np
import warnings
from pathlib import Path
from sklearn.preprocessing import LabelEncoder, StandardScaler
from sklearn.model_selection import train_test_split, cross_val_score, StratifiedKFold
from sklearn.metrics import classification_report, accuracy_score
from sklearn.ensemble import RandomForestClassifier, VotingClassifier
from sklearn.pipeline import Pipeline
from xgboost import XGBClassifier
import librosa

warnings.filterwarnings("ignore")
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

GTZAN_GENRES = [
    "blues", "classical", "country", "disco",
    "hiphop", "jazz", "metal", "pop", "reggae", "rock"
]

GENRE_MAP = {
    "blues":     "RnB_Soul",
    "classical": "Instrumental",
    "country":   "Folk_Country",
    "disco":     "Electronic_Dance",
    "hiphop":    "HipHop_Punjabi",
    "jazz":      "Instrumental",
    "metal":     "Rock_Metal",
    "pop":       "Pop",
    "reggae":    "Folk_Country",
    "rock":      "Rock_Metal",
}

SAVED_DIR = Path(__file__).parent / "saved"


def extract_features_from_file(file_path: str, sr: int = 22050) -> np.ndarray:
    """
    Extract a rich 140-dim feature vector.
    Adds delta + delta-delta MFCCs over the base version — key improvement
    for genre classification accuracy.
    """
    try:
        y, sr = librosa.load(file_path, sr=sr, mono=True, duration=30)

        # ── MFCC: mean + std + delta mean + delta-delta mean (13×4 = 52) ──
        mfcc         = librosa.feature.mfcc(y=y, sr=sr, n_mfcc=13)
        mfcc_delta   = librosa.feature.delta(mfcc)
        mfcc_delta2  = librosa.feature.delta(mfcc, order=2)
        mfcc_mean    = np.mean(mfcc, axis=1)
        mfcc_std     = np.std(mfcc, axis=1)
        mfcc_d_mean  = np.mean(mfcc_delta, axis=1)
        mfcc_d2_mean = np.mean(mfcc_delta2, axis=1)

        # ── Chroma: mean + std (12×2 = 24) ──────────────────────────────
        chroma      = librosa.feature.chroma_stft(y=y, sr=sr, n_chroma=12)
        chroma_mean = np.mean(chroma, axis=1)
        chroma_std  = np.std(chroma, axis=1)

        # ── Spectral features (7 scalars) ────────────────────────────────
        spec_centroid  = np.mean(librosa.feature.spectral_centroid(y=y, sr=sr))
        spec_bandwidth = np.mean(librosa.feature.spectral_bandwidth(y=y, sr=sr))
        spec_rolloff   = np.mean(librosa.feature.spectral_rolloff(y=y, sr=sr))
        spec_flatness  = np.mean(librosa.feature.spectral_flatness(y=y))
        spec_contrast  = np.mean(librosa.feature.spectral_contrast(y=y, sr=sr))
        spec_centroid_std = np.std(librosa.feature.spectral_centroid(y=y, sr=sr))
        spec_rolloff_std  = np.std(librosa.feature.spectral_rolloff(y=y, sr=sr))

        # ── Rhythm (3 scalars) ───────────────────────────────────────────
        tempo, beats  = librosa.beat.beat_track(y=y, sr=sr)
        tempo         = float(np.atleast_1d(tempo)[0])
        beat_strength = float(np.mean(librosa.onset.onset_strength(y=y, sr=sr)))
        zcr_mean      = float(np.mean(librosa.feature.zero_crossing_rate(y)))
        zcr_std       = float(np.std(librosa.feature.zero_crossing_rate(y)))

        # ── Energy (2 scalars) ───────────────────────────────────────────
        rms_mean = float(np.mean(librosa.feature.rms(y=y)))
        rms_std  = float(np.std(librosa.feature.rms(y=y)))

        # ── Tonnetz — tonal centroid (6 mean + 6 std = 12) ──────────────
        try:
            y_harm   = librosa.effects.harmonic(y)
            tonnetz  = librosa.feature.tonnetz(y=y_harm, sr=sr)
            ton_mean = np.mean(tonnetz, axis=1)
            ton_std  = np.std(tonnetz, axis=1)
        except Exception:
            ton_mean = np.zeros(6)
            ton_std  = np.zeros(6)

        # ── Mel spectrogram summary (11 mean + 11 std = 22) ─────────────
        mel     = librosa.feature.melspectrogram(y=y, sr=sr, n_mels=11)
        mel_db  = librosa.power_to_db(mel)
        mel_mean = np.mean(mel_db, axis=1)
        mel_std  = np.std(mel_db, axis=1)

        feature_vector = np.concatenate([
            mfcc_mean, mfcc_std, mfcc_d_mean, mfcc_d2_mean,   # 52
            chroma_mean, chroma_std,                            # 24
            [spec_centroid, spec_bandwidth, spec_rolloff,
             spec_flatness, spec_contrast,
             spec_centroid_std, spec_rolloff_std],              # 7
            [tempo, beat_strength, zcr_mean, zcr_std],         # 4
            [rms_mean, rms_std],                                # 2
            ton_mean, ton_std,                                  # 12
            mel_mean, mel_std,                                  # 22
        ])
        return feature_vector

    except Exception as e:
        logger.error(f"Feature extraction failed for {file_path}: {e}")
        return None


def build_gtzan_dataset(gtzan_dir: str) -> tuple:
    """Walk GTZAN directory structure and extract features from all audio files."""
    gtzan_path = Path(gtzan_dir)
    possible_roots = [
        gtzan_path,
        gtzan_path / "genres_original",
        gtzan_path / "genres",
        gtzan_path / "Data" / "genres_original",
    ]
    root = next((p for p in possible_roots if (p / "blues").exists()), None)
    if root is None:
        raise ValueError(
            f"Cannot find genre folders under {gtzan_dir}.\n"
            f"Expected: {gtzan_dir}/blues/, {gtzan_dir}/jazz/, etc."
        )
    logger.info(f"GTZAN root: {root}")

    X, y = [], []
    for genre in GTZAN_GENRES:
        genre_dir = root / genre
        audio_files = list(genre_dir.glob("*.wav")) + list(genre_dir.glob("*.mp3"))
        logger.info(f"  {genre}: {len(audio_files)} files")
        for audio_file in audio_files:
            if "jazz.00054" in str(audio_file):   # known corrupted file in GTZAN
                continue
            features = extract_features_from_file(str(audio_file))
            if features is not None:
                X.append(features)
                y.append(genre)

    logger.info(f"Extracted features from {len(X)} files")
    return np.array(X), np.array(y)


def train_and_save(gtzan_dir: str) -> dict:
    logger.info("=== Genre Classifier Training (v2 — Ensemble) ===")

    X, y_raw = build_gtzan_dataset(gtzan_dir)
    if len(X) == 0:
        raise ValueError(f"No GTZAN data found in {gtzan_dir}")

    le = LabelEncoder()
    y  = le.fit_transform(y_raw)

    scaler   = StandardScaler()
    X_scaled = scaler.fit_transform(X)

    X_train, X_test, y_train, y_test = train_test_split(
        X_scaled, y, test_size=0.2, random_state=42, stratify=y
    )

    # ── Random Forest — strong baseline for GTZAN ────────────────────────
    rf = RandomForestClassifier(
        n_estimators=500,
        max_depth=None,
        min_samples_split=4,
        min_samples_leaf=2,
        max_features="sqrt",
        class_weight="balanced",
        random_state=42,
        n_jobs=-1,
    )

    # ── XGBoost — shallower, more regularized than v1 ────────────────────
    xgb = XGBClassifier(
        n_estimators=300,
        max_depth=4,           # reduced from 6
        learning_rate=0.05,    # reduced from 0.1
        subsample=0.7,
        colsample_bytree=0.7,
        min_child_weight=3,    # prevents overfitting on small GTZAN
        reg_alpha=0.1,
        reg_lambda=1.0,
        eval_metric="mlogloss",
        random_state=42,
        n_jobs=-1,
        verbosity=0,
    )

    # ── Soft Voting Ensemble (RF + XGB) ──────────────────────────────────
    ensemble = VotingClassifier(
        estimators=[("rf", rf), ("xgb", xgb)],
        voting="soft",
        n_jobs=-1,
    )

    logger.info("Training ensemble (RF + XGBoost)... [~3-5 min]")
    ensemble.fit(X_train, y_train)

    # ── Evaluate ─────────────────────────────────────────────────────────
    y_pred = ensemble.predict(X_test)
    acc    = accuracy_score(y_test, y_pred)
    logger.info(f"\nTest Accuracy: {acc:.4f} ({acc*100:.1f}%)")
    logger.info(f"\n{classification_report(y_test, y_pred, target_names=le.classes_)}")

    # Stratified CV — more reliable than single split
    cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)
    cv_scores = cross_val_score(ensemble, X_scaled, y, cv=cv, scoring="accuracy", n_jobs=-1)
    logger.info(f"5-Fold Stratified CV: {cv_scores.mean():.4f} ± {cv_scores.std():.4f}")

    # ── Accuracy on collapsed 6-genre VibeFlow labels ────────────────────
    y_raw_pred    = le.inverse_transform(y_pred)
    y_raw_test    = le.inverse_transform(y_test)
    vf_pred       = [GENRE_MAP[g] for g in y_raw_pred]
    vf_test       = [GENRE_MAP[g] for g in y_raw_test]
    vf_acc        = accuracy_score(vf_test, vf_pred)
    logger.info(f"VibeFlow 6-Genre Accuracy: {vf_acc:.4f} ({vf_acc*100:.1f}%)")

    # ── Save artifacts ────────────────────────────────────────────────────
    SAVED_DIR.mkdir(parents=True, exist_ok=True)
    with open(SAVED_DIR / "xgb_genre_model.pkl", "wb") as f:
        pickle.dump(ensemble, f)
    with open(SAVED_DIR / "scaler.pkl", "wb") as f:
        pickle.dump(scaler, f)
    with open(SAVED_DIR / "label_encoder.pkl", "wb") as f:
        pickle.dump(le, f)

    logger.info(f"✅ Artifacts saved to {SAVED_DIR}")
    return {
        "test_accuracy":    round(acc, 4),
        "cv_mean":          round(cv_scores.mean(), 4),
        "cv_std":           round(cv_scores.std(), 4),
        "vibeflow_6genre_accuracy": round(vf_acc, 4),
        "n_classes":        len(le.classes_),
    }


if __name__ == "__main__":
    import sys
    gtzan_dir = sys.argv[1] if len(sys.argv) > 1 else "datasets/gtzan"
    result = train_and_save(gtzan_dir)
    print(f"\n{'='*50}")
    print(f"Training complete: {result}")
