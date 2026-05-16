"""
app/api/routes/library.py
Library management endpoints.
"""
from __future__ import annotations

from typing import Annotated, Optional

import structlog
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from app.db.repository import FeatureRepo, SongRepo
from app.db.session import AsyncSession, get_db
from app.ingestion.pipeline import run_ingestion

router = APIRouter(prefix="/library", tags=["Library"])
log = structlog.get_logger(__name__)


# ─── Response schemas ─────────────────────────────────────────────────────────

class SongOut(BaseModel):
    id: int
    title: str
    artist: str
    album: Optional[str]
    duration_sec: Optional[float]
    predicted_genre: Optional[str]
    genre_confidence: Optional[float]
    cluster_id: Optional[int]
    has_features: bool = False

    model_config = {"from_attributes": True}


class PaginatedSongs(BaseModel):
    items: list[SongOut]
    total: int
    page: int
    page_size: int
    total_pages: int


class LibraryStats(BaseModel):
    total_songs: int
    total_with_features: int
    genres: list[str]
    total_events: int


class ScanResult(BaseModel):
    scanned: int
    inserted: int
    updated: int
    errors: int


# ─── Endpoints ────────────────────────────────────────────────────────────────

@router.post("/scan", response_model=ScanResult, summary="Trigger ingestion scan")
async def scan_library(db: Annotated[AsyncSession, Depends(get_db)]) -> ScanResult:
    """
    Walk the MUSIC_DIR and insert/update all audio files in the database.
    Idempotent — safe to call multiple times.
    """
    summary = await run_ingestion(db, show_progress=False)
    return ScanResult(**summary)


@router.get("/songs", response_model=PaginatedSongs, summary="List songs")
async def list_songs(
    db: Annotated[AsyncSession, Depends(get_db)],
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    genre: Optional[str] = Query(None),
    artist: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
) -> PaginatedSongs:
    songs, total = await SongRepo.get_paginated(
        db, page=page, page_size=page_size, genre=genre, artist=artist, search=search
    )
    total_pages = max(1, (total + page_size - 1) // page_size)
    items = [
        SongOut(
            id=s.id,
            title=s.title,
            artist=s.artist,
            album=s.album,
            duration_sec=s.duration_sec,
            predicted_genre=s.predicted_genre,
            genre_confidence=s.genre_confidence,
            cluster_id=s.cluster_id,
            has_features=s.audio_feature is not None,
        )
        for s in songs
    ]
    return PaginatedSongs(items=items, total=total, page=page, page_size=page_size, total_pages=total_pages)


@router.get("/songs/{song_id}", response_model=SongOut, summary="Get song detail")
async def get_song(
    song_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> SongOut:
    song = await SongRepo.get_by_id(db, song_id)
    if not song:
        raise HTTPException(status_code=404, detail=f"Song {song_id} not found")
    return SongOut(
        id=song.id,
        title=song.title,
        artist=song.artist,
        album=song.album,
        duration_sec=song.duration_sec,
        predicted_genre=song.predicted_genre,
        genre_confidence=song.genre_confidence,
        cluster_id=song.cluster_id,
        has_features=song.audio_feature is not None,
    )


@router.get("/stats", response_model=LibraryStats, summary="Library statistics")
async def library_stats(
    db: Annotated[AsyncSession, Depends(get_db)],
) -> LibraryStats:
    total_songs = await SongRepo.count(db)
    total_with_features = await FeatureRepo.count_extracted(db)
    genres = await SongRepo.get_distinct_genres(db)

    from app.db.repository import EventRepo
    total_events = await EventRepo.count(db)

    return LibraryStats(
        total_songs=total_songs,
        total_with_features=total_with_features,
        genres=sorted(genres),
        total_events=total_events,
    )
