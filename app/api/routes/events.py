"""
app/api/routes/events.py
Event logging endpoints — called whenever the user plays/skips/completes a song.
"""
from __future__ import annotations

from typing import Annotated, Optional

import structlog
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from app.db.models import EventType
from app.db.repository import EventRepo
from app.db.session import AsyncSession, get_db
from app.services.events.logger import log_event

router = APIRouter(prefix="/events", tags=["Events"])
log = structlog.get_logger(__name__)


# ─── Request / Response schemas ───────────────────────────────────────────────

class EventRequest(BaseModel):
    song_id: int
    session_id: Optional[str] = None
    completion_ratio: float = Field(default=0.0, ge=0.0, le=1.0)


class EventResponse(BaseModel):
    event_id: int
    song_id: int
    event_type: str
    session_id: str
    completion_ratio: float


class EventHistoryItem(BaseModel):
    id: int
    song_id: int
    event_type: str
    timestamp: str
    session_id: str
    completion_ratio: float
    context_genre: Optional[str]


class PaginatedEvents(BaseModel):
    items: list[EventHistoryItem]
    total: int
    page: int
    page_size: int


# ─── Endpoints ────────────────────────────────────────────────────────────────

@router.post("/play", response_model=EventResponse, summary="Log play event")
async def log_play(
    body: EventRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> EventResponse:
    try:
        event = await log_event(
            db, body.song_id, EventType.PLAY, body.session_id, body.completion_ratio
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    return EventResponse(
        event_id=event.id,
        song_id=event.song_id,
        event_type=event.event_type.value,
        session_id=event.session_id,
        completion_ratio=event.completion_ratio,
    )


@router.post("/skip", response_model=EventResponse, summary="Log skip event")
async def log_skip(
    body: EventRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> EventResponse:
    try:
        event = await log_event(
            db, body.song_id, EventType.SKIP, body.session_id, body.completion_ratio
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    return EventResponse(
        event_id=event.id,
        song_id=event.song_id,
        event_type=event.event_type.value,
        session_id=event.session_id,
        completion_ratio=event.completion_ratio,
    )


@router.post("/complete", response_model=EventResponse, summary="Log completion event")
async def log_complete(
    body: EventRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> EventResponse:
    try:
        event = await log_event(
            db, body.song_id, EventType.COMPLETE, body.session_id, completion_ratio=1.0
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    return EventResponse(
        event_id=event.id,
        song_id=event.song_id,
        event_type=event.event_type.value,
        session_id=event.session_id,
        completion_ratio=event.completion_ratio,
    )


@router.post("/replay", response_model=EventResponse, summary="Log replay event")
async def log_replay(
    body: EventRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> EventResponse:
    try:
        event = await log_event(
            db, body.song_id, EventType.REPLAY, body.session_id, body.completion_ratio
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    return EventResponse(
        event_id=event.id,
        song_id=event.song_id,
        event_type=event.event_type.value,
        session_id=event.session_id,
        completion_ratio=event.completion_ratio,
    )


@router.get("/history", response_model=PaginatedEvents, summary="Listening history")
async def event_history(
    db: Annotated[AsyncSession, Depends(get_db)],
    page: int = 1,
    page_size: int = 50,
    song_id: Optional[int] = None,
) -> PaginatedEvents:
    events, total = await EventRepo.get_history(db, page=page, page_size=page_size, song_id=song_id)
    items = [
        EventHistoryItem(
            id=e.id,
            song_id=e.song_id,
            event_type=e.event_type.value,
            timestamp=e.timestamp.isoformat(),
            session_id=e.session_id,
            completion_ratio=e.completion_ratio,
            context_genre=e.context_genre,
        )
        for e in events
    ]
    return PaginatedEvents(items=items, total=total, page=page, page_size=page_size)
