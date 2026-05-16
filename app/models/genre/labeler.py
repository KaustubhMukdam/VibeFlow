"""
app/models/genre/labeler.py
Interactive genre labeling tool.
Exports representative sample songs per cluster for the user to review,
then applies confirmed genre names to all songs in each cluster.

Usage flow:
  1. `python -m app.cli label --export`  → writes cluster_samples.json
  2. User edits cluster_samples.json and sets "confirmed_genre" for each cluster
  3. `python -m app.cli label --apply`   → writes genres back to DB
"""
from __future__ import annotations

import json
from pathlib import Path

import structlog

from app.db.repository import SongRepo
from app.db.session import AsyncSession

log = structlog.get_logger(__name__)

SAMPLES_FILE = Path("data/interim/cluster_samples.json")


async def export_cluster_samples(
    db: AsyncSession,
    n_per_cluster: int = 5,
) -> dict:
    """
    For each cluster, pick n_per_cluster representative songs and write them
    to SAMPLES_FILE with a placeholder for the user to fill in confirmed_genre.

    Returns the samples dict.
    """
    songs = await SongRepo.get_all_active(db)
    clusters: dict[int, list[dict]] = {}

    for song in songs:
        if song.cluster_id is None:
            continue
        cid = song.cluster_id
        if cid not in clusters:
            clusters[cid] = []
        if len(clusters[cid]) < n_per_cluster:
            clusters[cid].append({
                "song_id": song.id,
                "title": song.title,
                "artist": song.artist,
                "file_path": song.file_path,
            })

    # Load any previously confirmed genres so we don't overwrite them
    existing: dict[str, str] = {}
    if SAMPLES_FILE.exists():
        try:
            old = json.loads(SAMPLES_FILE.read_text())
            for cid_str, entry in old.items():
                genre = entry.get("confirmed_genre", "")
                if genre and not genre.startswith("cluster_"):
                    existing[cid_str] = genre
        except Exception:
            pass  # corrupt file → start fresh

    output = {
        str(cid): {
            "cluster_id": cid,
            # keep the user's label if it exists, otherwise use the placeholder
            "confirmed_genre": existing.get(str(cid), f"cluster_{cid}"),
            "sample_songs": songs_list,
        }
        for cid, songs_list in sorted(clusters.items())
    }

    SAMPLES_FILE.parent.mkdir(parents=True, exist_ok=True)
    SAMPLES_FILE.write_text(json.dumps(output, indent=2, ensure_ascii=False))
    log.info("labeler.samples_exported", path=str(SAMPLES_FILE), clusters=len(output))
    return output


async def apply_genre_labels(
    db: AsyncSession,
    label_map: dict[int, str] | None = None,
) -> dict:
    """
    Read SAMPLES_FILE (or use label_map directly) and write confirmed genres
    back to all songs in each cluster.

    Returns {cluster_id: (genre, count_updated)}.
    """
    if label_map is None:
        if not SAMPLES_FILE.exists():
            raise FileNotFoundError(f"Run export first: {SAMPLES_FILE}")
        data = json.loads(SAMPLES_FILE.read_text())
        label_map = {
            int(cid): entry["confirmed_genre"]
            for cid, entry in data.items()
        }

    songs = await SongRepo.get_all_active(db)
    results: dict[int, tuple[str, int]] = {}

    for song in songs:
        if song.cluster_id is None:
            continue
        genre = label_map.get(song.cluster_id, f"cluster_{song.cluster_id}")
        await SongRepo.update_genre(
            db,
            song_id=song.id,
            genre=genre,
            cluster_id=song.cluster_id,
        )
        cid = song.cluster_id
        if cid not in results:
            results[cid] = (genre, 0)
        results[cid] = (results[cid][0], results[cid][1] + 1)

    log.info("labeler.genres_applied", clusters=len(results))
    return results
