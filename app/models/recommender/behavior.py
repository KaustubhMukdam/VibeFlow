"""
app/models/recommender/behavior.py
Behavior-based preference scoring.

Each listening event contributes to a song's score with time-decay weighting.
Recent events count more than old ones (exponential decay).

Score formula per event:
  delta = weight * (0.5 ^ (age_days / half_life_days))

Weights:
  COMPLETE : +3.0  (finished the song)
  REPLAY   : +4.0  (replayed it)
  PLAY     : +1.0  (started playing)
  SKIP     : -2.0  (skipped early: full penalty if < 20% completion)
              -0.5  (skipped late: partial skip, neutral-ish)
"""
from __future__ import annotations

from datetime import datetime, timezone

import numpy as np
import structlog

from app.db.models import EventType, ListeningEvent
from app.db.repository import EventRepo
from app.db.session import AsyncSession

log = structlog.get_logger(__name__)

# Event weights
_WEIGHTS = {
    EventType.COMPLETE: 3.0,
    EventType.REPLAY: 4.0,
    EventType.PLAY: 1.0,
    EventType.SKIP: None,  # computed dynamically
}

def _skip_weight(completion_ratio: float) -> float:
    """Stronger penalty for early skips, lighter for late skips."""
    if completion_ratio < 0.20:
        return -2.5
    elif completion_ratio < 0.50:
        return -1.5
    else:
        return -0.5  # played most of it, mild skip


def _decay(age_days: float, half_life_days: float) -> float:
    """Exponential decay: returns 1.0 for brand-new events, < 1.0 for older ones."""
    return float(0.5 ** (age_days / half_life_days))


async def get_behavior_scores(
    song_ids: list[int],
    db: AsyncSession,
    half_life_days: float = 7.0,
    max_history_days: int = 90,
) -> dict[int, float]:
    """
    Compute a behaviour-based score for each song_id.
    Songs with no events get a score of 0.0.

    Args:
        song_ids:         All candidate song IDs to score.
        db:               Async DB session.
        half_life_days:   How quickly old events lose weight.
        max_history_days: Events older than this are ignored entirely.

    Returns:
        dict mapping song_id → float score
    """
    events = await EventRepo.get_recent_events(db, hours=max_history_days * 24)
    now = datetime.utcnow()  # SQLite stores naive UTC timestamps
    scores: dict[int, float] = {sid: 0.0 for sid in song_ids}

    for event in events:
        if event.song_id not in scores:
            continue

        age_days = max(0.0, (now - event.timestamp).total_seconds() / 86400)
        decay = _decay(age_days, half_life_days)

        if event.event_type == EventType.SKIP:
            weight = _skip_weight(event.completion_ratio)
        else:
            weight = _WEIGHTS.get(event.event_type, 0.0)

        scores[event.song_id] += weight * decay

    return scores


async def get_recently_liked_songs(
    db: AsyncSession,
    hours: int = 72,
    min_score: float = 2.0,
    top_k: int = 10,
) -> list[int]:
    """
    Return song IDs that have strong positive behaviour in the last `hours`.
    Used as seeds for similarity-based recommendations.
    """
    events = await EventRepo.get_recent_events(db, hours=hours)
    now = datetime.utcnow()  # SQLite stores naive UTC timestamps
    scores: dict[int, float] = {}

    for event in events:
        age_days = max(0.0, (now - event.timestamp).total_seconds() / 86400)
        decay = _decay(age_days, half_life_days=1.0)  # tight decay for recency

        if event.event_type == EventType.SKIP:
            weight = _skip_weight(event.completion_ratio)
        else:
            weight = _WEIGHTS.get(event.event_type, 0.0)

        scores[event.song_id] = scores.get(event.song_id, 0.0) + weight * decay

    liked = [
        sid for sid, score in sorted(scores.items(), key=lambda x: x[1], reverse=True)
        if score >= min_score
    ]
    return liked[:top_k]
