"""
app/api/routes/genres.py
Genre management endpoints.
"""
from __future__ import annotations

from typing import Annotated, Optional

import structlog
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.db.repository import PreferenceRepo, SongRepo
from app.db.session import AsyncSession, get_db
from app.models.genre.labeler import apply_genre_labels, export_cluster_samples
from app.services.events.preference_scorer import compute_genre_preference_scores

router = APIRouter(prefix="/genres", tags=["Genres"])
log = structlog.get_logger(__name__)


# ─── Schemas ──────────────────────────────────────────────────────────────────

class GenreInfo(BaseModel):
    genre: str
    count: int
    preference_score: float


class GenreLabelRequest(BaseModel):
    label_map: dict[int, str]  # cluster_id → genre_name


class GenreLabelResponse(BaseModel):
    applied: dict[str, int]  # genre_name → songs_updated


class GenrePreference(BaseModel):
    genre: str
    score: float
    play_count: int
    skip_count: int


# ─── Endpoints ────────────────────────────────────────────────────────────────

@router.get("", response_model=list[GenreInfo], summary="List all genres")
async def list_genres(
    db: Annotated[AsyncSession, Depends(get_db)],
) -> list[GenreInfo]:
    """List all discovered genre clusters with song counts and preference scores."""
    genres = await SongRepo.get_distinct_genres(db)
    genre_prefs = await compute_genre_preference_scores(db)

    # Count songs per genre
    result = []
    for genre in sorted(genres):
        songs, total = await SongRepo.get_paginated(db, page=1, page_size=1, genre=genre)
        result.append(GenreInfo(
            genre=genre,
            count=total,
            preference_score=round(genre_prefs.get(genre, 0.0), 4),
        ))
    return result


@router.get("/{genre}/songs", summary="Songs in a genre")
async def songs_by_genre(
    genre: str,
    db: Annotated[AsyncSession, Depends(get_db)],
    page: int = 1,
    page_size: int = 50,
):
    songs, total = await SongRepo.get_paginated(db, page=page, page_size=page_size, genre=genre)
    if not songs and page == 1:
        raise HTTPException(status_code=404, detail=f"Genre '{genre}' not found")
    return {
        "genre": genre,
        "total": total,
        "page": page,
        "items": [{"id": s.id, "title": s.title, "artist": s.artist} for s in songs],
    }


@router.post("/label", response_model=GenreLabelResponse, summary="Apply genre labels to clusters")
async def label_genres(
    body: GenreLabelRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> GenreLabelResponse:
    """
    Apply user-confirmed genre names to KMeans cluster IDs.
    Example body: {"label_map": {"0": "Punjabi", "1": "Bollywood", "2": "English Pop"}}
    """
    results = await apply_genre_labels(db, label_map=body.label_map)
    applied = {genre: count for _, (genre, count) in results.items()}
    return GenreLabelResponse(applied=applied)


@router.get("/clusters/samples", summary="Export cluster sample songs for labeling")
async def cluster_samples(
    db: Annotated[AsyncSession, Depends(get_db)],
    n_per_cluster: int = 5,
):
    """
    Returns sample songs per cluster to help the user assign genre labels.
    """
    samples = await export_cluster_samples(db, n_per_cluster=n_per_cluster)
    return samples


@router.get("/preferences", response_model=list[GenrePreference], summary="Genre preference scores")
async def genre_preferences(
    db: Annotated[AsyncSession, Depends(get_db)],
) -> list[GenrePreference]:
    """Return the current genre preference scores learned from listening history."""
    prefs = await PreferenceRepo.get_all(db)
    return [
        GenrePreference(
            genre=p.genre,
            score=round(p.score, 4),
            play_count=p.play_count,
            skip_count=p.skip_count,
        )
        for p in prefs
    ]
