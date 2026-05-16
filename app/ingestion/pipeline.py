"""
app/ingestion/pipeline.py
Orchestrates the full ingestion flow:
  scan_library → normalise → upsert into DB

Idempotent: songs already in DB are updated (not duplicated).
Prints a tqdm progress bar when running from the CLI.
"""
from __future__ import annotations

import structlog
from tqdm import tqdm

from app.core.config import get_settings
from app.db.models import Song
from app.db.repository import SongRepo
from app.db.session import AsyncSession
from app.ingestion.scanner import SongMeta, scan_library

log = structlog.get_logger(__name__)


async def run_ingestion(db: AsyncSession, show_progress: bool = True) -> dict:
    """
    Run the full ingestion pipeline.
    Returns a summary dict: {scanned, inserted, updated, skipped}.
    """
    settings = get_settings()
    music_dir = settings.MUSIC_DIR

    # 1. Scan filesystem
    song_metas: list[SongMeta] = scan_library(music_dir)
    log.info("ingestion.scan_complete", total=len(song_metas))

    inserted = 0
    updated = 0
    errors = 0

    iterator = tqdm(song_metas, desc="Ingesting songs", unit="song") if show_progress else song_metas

    for meta in iterator:
        try:
            existing = await SongRepo.get_by_path(db, meta.file_path)
            song = Song(
                file_path=meta.file_path,
                file_hash=meta.file_hash,
                title=meta.title,
                artist=meta.artist,
                album=meta.album,
                duration_sec=meta.duration_sec,
            )
            if existing:
                # Update metadata but keep ML predictions intact
                existing.title = meta.title
                existing.artist = meta.artist
                existing.album = meta.album
                existing.duration_sec = meta.duration_sec
                existing.file_hash = meta.file_hash
                await db.flush()
                updated += 1
            else:
                db.add(song)
                await db.flush()
                inserted += 1
        except Exception as exc:
            log.warning("ingestion.row_error", path=meta.file_path, error=str(exc))
            errors += 1

    summary = {
        "scanned": len(song_metas),
        "inserted": inserted,
        "updated": updated,
        "errors": errors,
    }
    log.info("ingestion.complete", **summary)
    return summary
