"""
app/api/routes/recommendations.py
Recommendation endpoints.
"""
from __future__ import annotations

from datetime import date
from typing import Annotated, Optional

import structlog
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from app.db.repository import SongRepo
from app.db.session import AsyncSession, get_db
from app.models.recommender.engine import generate_weekend_playlist, recommend_daily
from app.models.recommender.similarity import get_similar_songs, is_matrix_ready

router = APIRouter(prefix="/recommendations", tags=["Recommendations"])
log = structlog.get_logger(__name__)


# ─── Response schemas ─────────────────────────────────────────────────────────

class RecommendedSong(BaseModel):
    rank: int
    song_id: int
    title: str
    artist: str
    predicted_genre: Optional[str]
    reason_code: str
    score: float


class DailyRecommendationResponse(BaseModel):
    date: str
    count: int
    recommendations: list[RecommendedSong]


class WeekendPlaylistResponse(BaseModel):
    week_start: str
    count: int
    song_ids: list[int]


class SimilarSongItem(BaseModel):
    song_id: int
    title: str
    artist: str
    predicted_genre: Optional[str]
    similarity_score: float


# ─── Endpoints ────────────────────────────────────────────────────────────────

@router.get("/daily", response_model=DailyRecommendationResponse, summary="Today's top picks")
async def daily_recommendations(
    db: Annotated[AsyncSession, Depends(get_db)],
    n: int = Query(10, ge=1, le=50),
) -> DailyRecommendationResponse:
    """
    Return today's personalised top-N song recommendations.
    Results are cached for the day — use /refresh to force regeneration.
    """
    recs = await recommend_daily(db, n=n)

    items: list[RecommendedSong] = []
    for r in recs:
        song = await SongRepo.get_by_id(db, r["song_id"])
        if song:
            items.append(RecommendedSong(
                rank=r["rank"],
                song_id=r["song_id"],
                title=song.title,
                artist=song.artist,
                predicted_genre=song.predicted_genre,
                reason_code=r["reason_code"],
                score=r["score"],
            ))

    return DailyRecommendationResponse(
        date=str(date.today()),
        count=len(items),
        recommendations=items,
    )


@router.post("/refresh", response_model=DailyRecommendationResponse, summary="Force-refresh today's recommendations")
async def refresh_recommendations(
    db: Annotated[AsyncSession, Depends(get_db)],
    n: int = Query(10, ge=1, le=50),
) -> DailyRecommendationResponse:
    recs = await recommend_daily(db, n=n, force_refresh=True)
    items = []
    for r in recs:
        song = await SongRepo.get_by_id(db, r["song_id"])
        if song:
            items.append(RecommendedSong(
                rank=r["rank"],
                song_id=r["song_id"],
                title=song.title,
                artist=song.artist,
                predicted_genre=song.predicted_genre,
                reason_code=r["reason_code"],
                score=r["score"],
            ))
    return DailyRecommendationResponse(
        date=str(date.today()),
        count=len(items),
        recommendations=items,
    )


@router.get("/weekend", response_model=WeekendPlaylistResponse, summary="Weekend playlist")
async def weekend_playlist(
    db: Annotated[AsyncSession, Depends(get_db)],
    n: int = Query(30, ge=5, le=100),
    refresh: bool = Query(False),
) -> WeekendPlaylistResponse:
    """
    Return this weekend's diversity-aware playlist.
    Pass ?refresh=true to regenerate.
    """
    song_ids = await generate_weekend_playlist(db, n=n, force_refresh=refresh)
    return WeekendPlaylistResponse(
        week_start=str(date.today()),
        count=len(song_ids),
        song_ids=song_ids,
    )


@router.get("/similar/{song_id}", response_model=list[SimilarSongItem], summary="Songs similar to a track")
async def similar_songs(
    song_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    top_k: int = Query(10, ge=1, le=50),
) -> list[SimilarSongItem]:
    """
    Return songs most acoustically similar to the given track.
    Requires feature extraction and similarity matrix to be built first.
    """
    if not is_matrix_ready():
        raise HTTPException(
            status_code=503,
            detail="Similarity matrix not ready. Run feature extraction and clustering first.",
        )
    song = await SongRepo.get_by_id(db, song_id)
    if not song:
        raise HTTPException(status_code=404, detail=f"Song {song_id} not found")

    similar_pairs = get_similar_songs(song_id, top_k=top_k)
    items = []
    for sim_id, score in similar_pairs:
        sim_song = await SongRepo.get_by_id(db, sim_id)
        if sim_song:
            items.append(SimilarSongItem(
                song_id=sim_song.id,
                title=sim_song.title,
                artist=sim_song.artist,
                predicted_genre=sim_song.predicted_genre,
                similarity_score=round(score, 4),
            ))
    return items
