"""
app/ingestion/scanner.py
Walks the local music directory, reads ID3/Vorbis/MP4 tags via mutagen,
and returns a list of SongMeta Pydantic models ready for DB ingestion.

Supported formats: .mp3, .flac, .m4a, .ogg, .wav
Skips non-audio files silently.
"""
from __future__ import annotations

import hashlib
import re
from pathlib import Path
from typing import Optional

import mutagen
import mutagen.id3
import mutagen.mp3
import mutagen.mp4
import mutagen.flac
import mutagen.oggvorbis
import structlog
from pydantic import BaseModel, field_validator

log = structlog.get_logger(__name__)

# File extensions we accept
AUDIO_EXTENSIONS = {".mp3", ".flac", ".m4a", ".ogg", ".wav"}


# ─── Data model ───────────────────────────────────────────────────────────────

class SongMeta(BaseModel):
    """Normalised song metadata extracted from file tags + filesystem."""
    file_path: str
    file_hash: Optional[str]
    title: str
    artist: str
    album: Optional[str]
    duration_sec: Optional[float]

    @field_validator("title", "artist", mode="before")
    @classmethod
    def strip_whitespace(cls, v: str) -> str:
        return str(v).strip() if v else v


# ─── Tag readers ──────────────────────────────────────────────────────────────

def _read_mp3_tags(path: Path) -> dict:
    try:
        audio = mutagen.mp3.MP3(path, ID3=mutagen.id3.ID3)
        tags = audio.tags or {}
        return {
            "title": str(tags.get("TIT2", "")).strip() or None,
            "artist": str(tags.get("TPE1", "")).strip() or None,
            "album": str(tags.get("TALB", "")).strip() or None,
            "duration_sec": audio.info.length if audio.info else None,
        }
    except Exception as exc:
        log.debug("scanner.mp3_tag_error", path=str(path), error=str(exc))
        return {}


def _read_m4a_tags(path: Path) -> dict:
    try:
        audio = mutagen.mp4.MP4(path)
        tags = audio.tags or {}
        return {
            "title": str(tags.get("©nam", [""])[0]).strip() or None,
            "artist": str(tags.get("©ART", [""])[0]).strip() or None,
            "album": str(tags.get("©alb", [""])[0]).strip() or None,
            "duration_sec": audio.info.length if audio.info else None,
        }
    except Exception as exc:
        log.debug("scanner.m4a_tag_error", path=str(path), error=str(exc))
        return {}


def _read_flac_tags(path: Path) -> dict:
    try:
        audio = mutagen.flac.FLAC(path)
        tags = audio.tags or {}
        return {
            "title": tags.get("title", [None])[0],
            "artist": tags.get("artist", [None])[0],
            "album": tags.get("album", [None])[0],
            "duration_sec": audio.info.length if audio.info else None,
        }
    except Exception as exc:
        log.debug("scanner.flac_tag_error", path=str(path), error=str(exc))
        return {}


def _read_ogg_tags(path: Path) -> dict:
    try:
        audio = mutagen.oggvorbis.OggVorbis(path)
        tags = audio.tags or {}
        return {
            "title": tags.get("title", [None])[0],
            "artist": tags.get("artist", [None])[0],
            "album": tags.get("album", [None])[0],
            "duration_sec": audio.info.length if audio.info else None,
        }
    except Exception as exc:
        log.debug("scanner.ogg_tag_error", path=str(path), error=str(exc))
        return {}


def _read_tags(path: Path) -> dict:
    ext = path.suffix.lower()
    readers = {
        ".mp3": _read_mp3_tags,
        ".m4a": _read_m4a_tags,
        ".flac": _read_flac_tags,
        ".ogg": _read_ogg_tags,
    }
    reader = readers.get(ext)
    if reader:
        return reader(path)
    # WAV — minimal metadata support
    try:
        audio = mutagen.File(path)
        if audio:
            return {"duration_sec": getattr(audio.info, "length", None)}
    except Exception:
        pass
    return {}


# ─── Hash helper ──────────────────────────────────────────────────────────────

def _file_hash(path: Path, chunk_size: int = 65536) -> str:
    """MD5 of the first chunk_size bytes — fast enough for deduplication."""
    h = hashlib.md5()
    try:
        with open(path, "rb") as f:
            h.update(f.read(chunk_size))
    except OSError:
        pass
    return h.hexdigest()


# ─── Title fallback ───────────────────────────────────────────────────────────

_CLEAN_PATTERNS = [
    r"\(SPOTISAVER\)", r"\(DJJOhAL\.Com\)", r"\(Raag\.Fm\)",
    r"\(Mr-Jat\.in\)", r"\(PenduJatt\.Com\.Se\)", r"\(KoshalWorld\.Com\)",
    r"\(online-audio-converter.*\)", r"^\[SPOTDOWNLOADER\.COM\]\s*",
    r"^SpotiDown\.App\s*-\s*", r"^SpotiDownloader\.com\s*-\s*",
    r"^SpotifyMate\.com\s*-\s*", r"\s*\d{3}\s*Kbps", r"\.mp3$",
]
_CLEAN_RE = re.compile("|".join(_CLEAN_PATTERNS), re.IGNORECASE)


def _title_from_filename(path: Path) -> str:
    """Best-effort title derived from the filename when tags are missing."""
    stem = path.stem
    cleaned = _CLEAN_RE.sub("", stem).strip(" -_")
    return cleaned if cleaned else path.stem


# ─── Public API ───────────────────────────────────────────────────────────────

def scan_library(music_dir: Path) -> list[SongMeta]:
    """
    Walk music_dir recursively and return a SongMeta for each audio file.
    Non-audio files are silently skipped.
    """
    if not music_dir.exists():
        raise FileNotFoundError(f"Music directory not found: {music_dir}")

    songs: list[SongMeta] = []
    skipped = 0

    all_files = [p for p in music_dir.rglob("*") if p.is_file()]
    audio_files = [p for p in all_files if p.suffix.lower() in AUDIO_EXTENSIONS]

    log.info(
        "scanner.started",
        music_dir=str(music_dir),
        total_files=len(all_files),
        audio_files=len(audio_files),
    )

    for path in audio_files:
        try:
            tags = _read_tags(path)
            title = tags.get("title") or _title_from_filename(path)
            artist = tags.get("artist") or "Unknown Artist"
            song = SongMeta(
                file_path=str(path.resolve()),
                file_hash=_file_hash(path),
                title=title,
                artist=artist,
                album=tags.get("album"),
                duration_sec=tags.get("duration_sec"),
            )
            songs.append(song)
        except Exception as exc:
            log.warning("scanner.file_skipped", path=str(path), error=str(exc))
            skipped += 1

    log.info("scanner.done", found=len(songs), skipped=skipped)
    return songs
