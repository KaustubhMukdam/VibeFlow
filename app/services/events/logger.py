"""
app/services/events/logger.py
Event logging service — the bridge between user actions and the DB.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

import structlog

from app.db.models import EventType, ListeningEvent
from app.db.repository import EventRepo, PreferenceRepo, SongRepo
from app.db.session import AsyncSession

log = structlog.get_logger(__name__)

# How long without any event before we consider a new session started
SESSION_TIMEOUT_MINUTES = 30

# Points applied to genre preference per event type
_GENRE_SCORE_DELTAS = {
    EventType.PLAY: 0.5,
    EventType.COMPLETE: 2.0,
    EventType.REPLAY: 3.0,
    EventType.SKIP: -1.0,
}


async def log_event(
    db: AsyncSession,
    song_id: int,
    event_type: EventType,
    session_id: str | None = None,
    completion_ratio: float = 0.0,
) -> ListeningEvent:
    """
    Record a single user interaction event and update genre preferences.

    If session_id is None, attempt to reuse the current session or create a new one.
    """
    # Validate song exists
    song = await SongRepo.get_by_id(db, song_id)
    if song is None:
        raise ValueError(f"Song {song_id} not found")

    # Resolve session ID
    resolved_session = session_id or await _resolve_session(db)

    # Determine context genre from the current session
    context_genre = song.predicted_genre

    event = ListeningEvent(
        song_id=song_id,
        event_type=event_type,
        session_id=resolved_session,
        completion_ratio=max(0.0, min(1.0, completion_ratio)),
        context_genre=context_genre,
    )
    await EventRepo.log(db, event)

    # Update running genre preference scores
    if context_genre:
        delta = _GENRE_SCORE_DELTAS.get(event_type, 0.0)
        # Apply stronger skip penalty for early skips
        if event_type == EventType.SKIP and completion_ratio < 0.20:
            delta = -2.0
        await PreferenceRepo.upsert_genre_score(db, context_genre, delta, event_type)

    log.info(
        "event.logged",
        song_id=song_id,
        event_type=event_type.value,
        session=resolved_session,
        completion=round(completion_ratio, 2),
    )
    return event


async def _resolve_session(db: AsyncSession) -> str:
    """
    Reuse the current session if the last event was within SESSION_TIMEOUT_MINUTES.
    Otherwise create a new session UUID.
    """
    recent = await EventRepo.get_recent_events(db, hours=1)
    if recent:
        last_event = recent[0]
        age = datetime.now(timezone.utc) - last_event.timestamp
        if age < timedelta(minutes=SESSION_TIMEOUT_MINUTES):
            return last_event.session_id
    return str(uuid.uuid4())
