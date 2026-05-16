"""
app/services/events/preference_scorer.py
Computes normalised genre preference scores from the DB.
Used by the recommendation engine for genre-aware reranking.
"""
from __future__ import annotations

import structlog

from app.db.repository import PreferenceRepo
from app.db.session import AsyncSession

log = structlog.get_logger(__name__)


async def compute_genre_preference_scores(
    db: AsyncSession,
) -> dict[str, float]:
    """
    Load all UserPreference rows and return normalised scores in [0, 1].

    Genres with negative scores are clamped to 0 for recommendation purposes
    (we use negative scores for filtering, not for anti-recommendations).

    Returns:
        dict mapping genre → normalised preference score.
    """
    prefs = await PreferenceRepo.get_all(db)
    if not prefs:
        return {}

    raw: dict[str, float] = {p.genre: max(0.0, p.score) for p in prefs}
    total = sum(raw.values())

    if total == 0:
        # All genres have equal weight when no positive events exist
        n = len(raw)
        return {g: 1.0 / n for g in raw} if n > 0 else {}

    return {genre: score / total for genre, score in raw.items()}


async def get_current_session_genre(
    db: AsyncSession,
    session_id: str,
) -> str | None:
    """
    Infer the dominant genre in the given session.
    Used for real-time reranking ('what genre am I in the mood for right now').
    """
    from app.db.repository import EventRepo
    from app.db.models import EventType

    events = await EventRepo.get_session_events(db, session_id)
    if not events:
        return None

    genre_counts: dict[str, int] = {}
    for event in events:
        if event.context_genre and event.event_type != EventType.SKIP:
            genre_counts[event.context_genre] = genre_counts.get(event.context_genre, 0) + 1

    if not genre_counts:
        return None

    return max(genre_counts, key=genre_counts.get)
