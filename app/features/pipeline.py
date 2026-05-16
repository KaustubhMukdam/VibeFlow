"""
app/features/pipeline.py
Batch feature extraction pipeline.

Fetches all songs without AudioFeature rows from the DB, extracts features
using a ThreadPoolExecutor (CPU-bound work runs in parallel threads),
and upserts results back into the DB in batches.

Includes a JSON checkpoint file so the process can resume after interruption.
"""
from __future__ import annotations

import asyncio
import json
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import structlog
from tqdm import tqdm

from app.core.config import get_settings
from app.db.models import AudioFeature
from app.db.repository import FeatureRepo, SongRepo
from app.db.session import AsyncSession
from app.features.extractor import AudioFeatureVector, extract_features

log = structlog.get_logger(__name__)

CHECKPOINT_FILE = Path("data/interim/extraction_checkpoint.json")


# ─── Checkpoint helpers ───────────────────────────────────────────────────────

def _load_checkpoint() -> set[int]:
    """Return a set of song_ids already successfully extracted."""
    if CHECKPOINT_FILE.exists():
        try:
            data = json.loads(CHECKPOINT_FILE.read_text())
            return set(data.get("completed", []))
        except Exception:
            return set()
    return set()


def _save_checkpoint(completed_ids: set[int]) -> None:
    CHECKPOINT_FILE.parent.mkdir(parents=True, exist_ok=True)
    CHECKPOINT_FILE.write_text(
        json.dumps({"completed": sorted(completed_ids), "updated_at": datetime.now(timezone.utc).isoformat()})
    )


# ─── Worker (runs in thread pool) ────────────────────────────────────────────

def _extract_worker(
    song_id: int,
    file_path: str,
    sr: int,
    duration: Optional[float],
) -> Optional[AudioFeatureVector]:
    """Called from ThreadPoolExecutor — no async here."""
    return extract_features(
        file_path=Path(file_path),
        song_id=song_id,
        sr=sr,
        duration=duration,
    )


# ─── Main pipeline ────────────────────────────────────────────────────────────

async def run_feature_extraction(
    db: AsyncSession,
    show_progress: bool = True,
    batch_size: int = 50,
) -> dict:
    """
    Run batch feature extraction for all songs missing AudioFeature rows.
    Returns a summary dict: {total, extracted, skipped, failed}.
    """
    settings = get_settings()
    max_workers = settings.FEATURE_EXTRACTION_WORKERS
    sr = settings.SAMPLE_RATE
    duration = settings.ANALYSIS_DURATION

    # Find songs without features
    songs = await SongRepo.get_songs_without_features(db)
    already_done = _load_checkpoint()
    pending = [s for s in songs if s.id not in already_done]

    log.info(
        "feature_pipeline.started",
        total_pending=len(pending),
        already_extracted=len(already_done),
        workers=max_workers,
    )

    if not pending:
        log.info("feature_pipeline.nothing_to_do")
        return {"total": 0, "extracted": 0, "skipped": 0, "failed": 0}

    extracted = 0
    failed = 0
    completed_ids: set[int] = set(already_done)
    results_buffer: list[AudioFeatureVector] = []

    bar = tqdm(total=len(pending), desc="Extracting features", unit="song") if show_progress else None

    # We run CPU-bound extraction in a ThreadPoolExecutor.
    # Results are collected and flushed to DB in batches to avoid huge transactions.
    loop = asyncio.get_running_loop()

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {
            executor.submit(_extract_worker, s.id, s.file_path, sr, duration): s
            for s in pending
        }

        for future in as_completed(futures):
            song = futures[future]
            try:
                fvec: Optional[AudioFeatureVector] = future.result()
                if fvec is not None:
                    results_buffer.append(fvec)
                    completed_ids.add(song.id)
                    extracted += 1
                else:
                    failed += 1
            except Exception as exc:
                log.warning("feature_pipeline.worker_error", song_id=song.id, error=str(exc))
                failed += 1

            if bar:
                bar.update(1)

            # Flush to DB in batches
            if len(results_buffer) >= batch_size:
                await _flush_batch(db, results_buffer)
                _save_checkpoint(completed_ids)
                results_buffer.clear()

    # Flush remaining
    if results_buffer:
        await _flush_batch(db, results_buffer)
        _save_checkpoint(completed_ids)

    if bar:
        bar.close()

    summary = {
        "total": len(pending),
        "extracted": extracted,
        "skipped": len(already_done),
        "failed": failed,
    }
    log.info("feature_pipeline.complete", **summary)
    return summary


async def _flush_batch(db: AsyncSession, fvecs: list[AudioFeatureVector]) -> None:
    """Persist a batch of AudioFeatureVector objects to the database."""
    for fvec in fvecs:
        feature = AudioFeature(**fvec.to_orm_kwargs())
        await FeatureRepo.upsert(db, feature)
    await db.commit()
    log.debug("feature_pipeline.batch_saved", count=len(fvecs))
