"""
Session routes — session management, track logging, bandit queue, and auto-grouping.

Features:
  - POST /start           — manually start a new session
  - POST /{id}/track      — log a play event + auto-create new session if >30min gap
  - GET  /{id}/next       — bandit selects next songs for the queue
  - POST /{id}/end        — mark session as ended
  - GET  /{id}            — get session details with all tracks
  - GET  /recent          — get recent sessions for the history page
"""
import uuid
from datetime import datetime, timezone, timedelta
from typing import Optional

from fastapi import APIRouter, Query
from pydantic import BaseModel
from sqlalchemy import func, desc

from db import SessionLocal
from db.models import Session, ListeningHistory, Song

router = APIRouter()

# ── Config ───────────────────────────────────────────────────────────────────
SESSION_GAP_MINUTES = 30   # Auto-create new session if gap > this


# ── Pydantic Models ──────────────────────────────────────────────────────────
class SessionStartResponse(BaseModel):
    session_id: str
    started_at: str


class TrackPlayRequest(BaseModel):
    song_id: str
    play_duration_ms: int
    song_duration_ms: int
    skipped: bool = False
    skip_time_ms: Optional[int] = None


# ── POST /start ──────────────────────────────────────────────────────────────
@router.post("/start", response_model=SessionStartResponse)
def start_session():
    """Start a new listening session."""
    db = SessionLocal()
    try:
        session_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc)
        session = Session(
            session_id=session_id,
            started_at=now,
        )
        db.add(session)
        db.commit()
        return SessionStartResponse(
            session_id=session_id,
            started_at=now.isoformat(),
        )
    finally:
        db.close()


# ── POST /{session_id}/track ─────────────────────────────────────────────────
@router.post("/{session_id}/track")
def log_track_play(session_id: str, payload: TrackPlayRequest):
    """
    Log a song play event and update the bandit in real time.
    Auto-creates a new session if >30 min since last play in this session.
    """
    db = SessionLocal()
    try:
        now = datetime.now(timezone.utc)

        # ── Auto-grouping: check gap since last play ─────────────────────
        last_play = (
            db.query(ListeningHistory)
            .filter(ListeningHistory.session_id == session_id)
            .order_by(ListeningHistory.played_at.desc())
            .first()
        )

        active_session_id = session_id
        if last_play and (now - last_play.played_at) > timedelta(minutes=SESSION_GAP_MINUTES):
            # Gap > 30 min → auto-create new session
            new_id = str(uuid.uuid4())
            new_session = Session(session_id=new_id, started_at=now)
            db.add(new_session)
            active_session_id = new_id

            # End the old session
            old_session = db.query(Session).filter_by(session_id=session_id).first()
            if old_session and not old_session.ended_at:
                old_session.ended_at = last_play.played_at

        # ── Log the play event ───────────────────────────────────────────
        record = ListeningHistory(
            song_id=payload.song_id,
            played_at=now,
            play_duration_ms=payload.play_duration_ms,
            song_duration_ms=payload.song_duration_ms,
            skipped=payload.skipped,
            skip_time_ms=payload.skip_time_ms,
            source="local",
            session_id=active_session_id,
        )
        db.add(record)

        session = db.query(Session).filter_by(session_id=active_session_id).first()
        if session:
            session.song_count = (session.song_count or 0) + 1

        db.commit()

    finally:
        db.close()

    # Update bandit AFTER DB commit
    from models.bandit import update_bandit, compute_reward
    reward = compute_reward(
        payload.play_duration_ms,
        payload.song_duration_ms,
        payload.skipped,
    )
    update_bandit(payload.song_id, reward)

    return {
        "status": "logged",
        "session_id": active_session_id,
        "song_id": payload.song_id,
        "reward": reward,
        "new_session": active_session_id != session_id,
    }


# ── GET /{session_id}/next ───────────────────────────────────────────────────
@router.get("/{session_id}/next")
def get_next_songs(session_id: str, count: int = Query(default=3, ge=1, le=10)):
    """
    Bandit selects the next best songs for the session queue.
    This is the core real-time queue adaptation feature from PLANNING.md.
    """
    from models.bandit import select_next_songs
    songs = select_next_songs(session_id, count=count)
    return {"session_id": session_id, "queue": songs, "count": len(songs)}


# ── POST /{session_id}/end ───────────────────────────────────────────────────
@router.post("/{session_id}/end")
def end_session(session_id: str):
    """Mark a session as ended and compute final stats."""
    db = SessionLocal()
    try:
        session = db.query(Session).filter_by(session_id=session_id).first()
        if session:
            session.ended_at = datetime.now(timezone.utc)

            # Calculate skip rate
            history = db.query(ListeningHistory).filter_by(session_id=session_id).all()
            if history:
                skips = sum(1 for h in history if h.skipped)
                session.skip_rate = round(skips / len(history), 4)

            db.commit()
            return {
                "status": "ended",
                "session_id": session_id,
                "songs_played": session.song_count,
                "skip_rate": session.skip_rate,
            }
        return {"status": "not_found"}
    finally:
        db.close()


# ── GET /{session_id} ────────────────────────────────────────────────────────
@router.get("/{session_id}")
def get_session(session_id: str):
    """Get session details including all tracks played."""
    db = SessionLocal()
    try:
        session = db.query(Session).filter_by(session_id=session_id).first()
        if not session:
            return {"error": "Session not found"}
        history = (
            db.query(ListeningHistory)
            .filter_by(session_id=session_id)
            .order_by(ListeningHistory.played_at.asc())
            .all()
        )
        return {
            "session_id": session.session_id,
            "started_at": session.started_at,
            "ended_at": session.ended_at,
            "song_count": session.song_count,
            "skip_rate": session.skip_rate,
            "tracks": [
                {
                    "song_id": h.song_id,
                    "played_at": h.played_at,
                    "play_duration_ms": h.play_duration_ms,
                    "skipped": h.skipped,
                }
                for h in history
            ],
        }
    finally:
        db.close()


# ── GET /recent ──────────────────────────────────────────────────────────────
@router.get("/")
def get_recent_sessions(limit: int = Query(default=10, ge=1, le=50)):
    """
    Get recent sessions with their tracks — used by the Listening History page.
    Returns sessions ordered by most recent, each with embedded track details.
    """
    db = SessionLocal()
    try:
        sessions = (
            db.query(Session)
            .order_by(Session.started_at.desc())
            .limit(limit)
            .all()
        )

        result = []
        for s in sessions:
            tracks = (
                db.query(ListeningHistory, Song)
                .join(Song, ListeningHistory.song_id == Song.song_id)
                .filter(ListeningHistory.session_id == s.session_id)
                .order_by(ListeningHistory.played_at.asc())
                .all()
            )

            result.append({
                "session_id": s.session_id,
                "started_at": s.started_at.isoformat() if s.started_at else None,
                "ended_at": s.ended_at.isoformat() if s.ended_at else None,
                "song_count": s.song_count or len(tracks),
                "skip_rate": s.skip_rate,
                "tracks": [
                    {
                        "song_id": h.song_id,
                        "title": song.title,
                        "artist": song.artist,
                        "genre": song.genre,
                        "played_at": h.played_at.isoformat() if h.played_at else None,
                        "play_duration_ms": h.play_duration_ms,
                        "skipped": h.skipped,
                    }
                    for h, song in tracks
                ],
            })

        return {"sessions": result, "total": len(result)}
    finally:
        db.close()
