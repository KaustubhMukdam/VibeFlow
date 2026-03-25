# api/routers/session.py
import uuid
from datetime import datetime, timezone
from fastapi import APIRouter
from pydantic import BaseModel
from db import SessionLocal
from db.models import Session, ListeningHistory

router = APIRouter()


class SessionStartResponse(BaseModel):
    session_id: str
    started_at: str


class TrackPlayRequest(BaseModel):
    song_id: str
    play_duration_ms: int
    song_duration_ms: int
    skipped: bool = False
    skip_time_ms: int = None


@router.post("/start", response_model=SessionStartResponse)
def start_session():
    """Start a new listening session."""
    db = SessionLocal()
    try:
        session_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc)
        session = Session(
            session_id = session_id,
            started_at = now,
        )
        db.add(session)
        db.commit()
        return SessionStartResponse(
            session_id = session_id,
            started_at = now.isoformat(),
        )
    finally:
        db.close()


@router.post("/{session_id}/track")
def log_track_play(session_id: str, payload: TrackPlayRequest):
    """Log a song play event and update the bandit in real time."""
    db = SessionLocal()
    try:
        record = ListeningHistory(
            song_id          = payload.song_id,
            played_at        = datetime.now(timezone.utc),
            play_duration_ms = payload.play_duration_ms,
            song_duration_ms = payload.song_duration_ms,
            skipped          = payload.skipped,
            skip_time_ms     = payload.skip_time_ms,
            source           = "local",
            session_id       = session_id,
        )
        db.add(record)

        session = db.query(Session).filter_by(session_id=session_id).first()
        if session:
            session.song_count = (session.song_count or 0) + 1

        db.commit()

    finally:
        db.close()

    # Update bandit AFTER DB commit — async-safe
    from models.bandit import update_bandit, compute_reward
    reward = compute_reward(
        payload.play_duration_ms,
        payload.song_duration_ms,
        payload.skipped,
    )
    update_bandit(payload.song_id, reward)

    return {
        "status":  "logged",
        "song_id": payload.song_id,
        "reward":  reward,
    }


@router.post("/{session_id}/end")
def end_session(session_id: str):
    """Mark a session as ended."""
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
            return {"status": "ended", "session_id": session_id, "songs_played": session.song_count}
        return {"status": "not_found"}
    finally:
        db.close()


@router.get("/{session_id}")
def get_session(session_id: str):
    """Get session details including all tracks played."""
    db = SessionLocal()
    try:
        session = db.query(Session).filter_by(session_id=session_id).first()
        if not session:
            return {"error": "Session not found"}
        history = db.query(ListeningHistory).filter_by(session_id=session_id).all()
        return {
            "session_id":  session.session_id,
            "started_at":  session.started_at,
            "ended_at":    session.ended_at,
            "song_count":  session.song_count,
            "skip_rate":   session.skip_rate,
            "tracks": [
                {
                    "song_id":          h.song_id,
                    "played_at":        h.played_at,
                    "play_duration_ms": h.play_duration_ms,
                    "skipped":          h.skipped,
                }
                for h in history
            ],
        }
    finally:
        db.close()
