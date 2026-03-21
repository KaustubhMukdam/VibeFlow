import os
import hashlib
import logging
import warnings
import numpy as np
import librosa
from mutagen import File as MutagenFile
from mutagen.id3 import ID3NoHeaderError
from pathlib import Path
from typing import Optional

warnings.filterwarnings("ignore", category=UserWarning)
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

SUPPORTED_EXTENSIONS = {".mp3", ".flac", ".wav", ".m4a", ".ogg", ".aac"}


def scan_library(music_dir: str) -> list[dict]:
    songs = []
    music_path = Path(music_dir)

    if not music_path.exists():
        logger.error(f"Music directory not found: {music_dir}")
        return songs

    all_files = [
        f for f in music_path.rglob("*")
        if f.suffix.lower() in SUPPORTED_EXTENSIONS
    ]
    logger.info(f"Found {len(all_files)} audio files in {music_dir}")

    for idx, file_path in enumerate(all_files):
        try:
            logger.info(f"[{idx+1}/{len(all_files)}] Processing: {file_path.name}")
            song_data = extract_song_data(str(file_path))
            if song_data:
                songs.append(song_data)
        except Exception as e:
            logger.warning(f"Skipping {file_path.name}: {e}")
            continue

    logger.info(f"Successfully processed {len(songs)}/{len(all_files)} files")
    return songs


def extract_song_data(file_path: str) -> Optional[dict]:
    metadata      = _extract_metadata(file_path)
    audio_features = _extract_audio_features(file_path)

    if not audio_features:
        return None

    return {
        "song_id":           _compute_file_hash(file_path),
        "title":             metadata.get("title") or Path(file_path).stem,
        "artist":            metadata.get("artist") or "Unknown Artist",
        "album":             metadata.get("album"),
        "duration_ms":       audio_features.get("duration_ms"),
        "source":            "local",
        "file_path":         str(Path(file_path).resolve()),
        "tempo":             audio_features.get("tempo"),
        "energy":            audio_features.get("energy"),
        "loudness":          audio_features.get("loudness"),
        "acousticness":      audio_features.get("acousticness"),
        "instrumentalness":  audio_features.get("instrumentalness"),
        "speechiness":       audio_features.get("speechiness"),
        "mfcc_vector":       audio_features.get("mfcc_vector"),
        "danceability":      None,
        "valence":           None,
        "genre":             None,
        "genre_confidence":  None,
    }


def _extract_metadata(file_path: str) -> dict:
    meta = {}
    try:
        audio = MutagenFile(file_path, easy=True)
        if audio is None:
            return meta
        meta["title"]  = _first(audio.get("title"))
        meta["artist"] = _first(audio.get("artist"))
        meta["album"]  = _first(audio.get("album"))
    except (ID3NoHeaderError, Exception) as e:
        logger.debug(f"Metadata read failed for {file_path}: {e}")
    return meta


def _extract_audio_features(file_path: str, sr: int = 22050) -> Optional[dict]:
    try:
        # Load first 60 seconds only for speed
        y, sr = librosa.load(file_path, sr=sr, mono=True, duration=60)

        duration_ms = int(librosa.get_duration(y=y, sr=sr) * 1000)

        tempo, _ = librosa.beat.beat_track(y=y, sr=sr)
        tempo = float(np.atleast_1d(tempo)[0])

        rms      = librosa.feature.rms(y=y)
        energy   = float(np.mean(rms))
        loudness = float(librosa.amplitude_to_db(rms).mean())

        spec_flatness = float(np.mean(librosa.feature.spectral_flatness(y=y)))
        acousticness  = float(max(0.0, min(1.0, 1.0 - spec_flatness * 100)))

        zcr = float(np.mean(librosa.feature.zero_crossing_rate(y)))
        spec_centroid = float(np.mean(librosa.feature.spectral_centroid(y=y, sr=sr)))

        instrumentalness = float(max(0.0, min(1.0, 1.0 - (zcr * 10 + spec_centroid / sr))))
        speechiness      = float(min(1.0, zcr * 2))

        mfcc        = librosa.feature.mfcc(y=y, sr=sr, n_mfcc=13)
        mfcc_vector = np.mean(mfcc, axis=1).tolist()

        return {
            "duration_ms":      duration_ms,
            "tempo":            round(tempo, 2),
            "energy":           round(energy, 6),
            "loudness":         round(loudness, 4),
            "acousticness":     round(acousticness, 4),
            "instrumentalness": round(instrumentalness, 4),
            "speechiness":      round(speechiness, 4),
            "mfcc_vector":      mfcc_vector,
        }
    except Exception as e:
        logger.error(f"librosa failed on {file_path}: {e}")
        return None


def _compute_file_hash(file_path: str) -> str:
    md5 = hashlib.md5()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            md5.update(chunk)
    return f"local_{md5.hexdigest()}"


def _first(tag_value) -> Optional[str]:
    if isinstance(tag_value, list) and tag_value:
        return str(tag_value[0]).strip()
    return None
