"""
app/db/models.py
All SQLAlchemy ORM models for VibeFlow.

Tables:
    songs               – core song metadata + ML predictions
    audio_features      – librosa-extracted feature vectors per song
    listening_events    – per-event behavioural log (play/skip/complete/replay)
    user_preferences    – running genre preference scores
    daily_recommendations – cached daily top-N picks
    weekend_playlists   – cached weekend playlists
"""
from __future__ import annotations

import enum
import json
from datetime import date, datetime, timezone
from typing import List, Optional

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


# ─── Helpers ──────────────────────────────────────────────────────────────────

def utcnow() -> datetime:
    return datetime.now(timezone.utc)


# ─── Enums ────────────────────────────────────────────────────────────────────

class EventType(str, enum.Enum):
    PLAY = "play"
    SKIP = "skip"
    COMPLETE = "complete"
    REPLAY = "replay"


# ─── Song ─────────────────────────────────────────────────────────────────────

class Song(Base):
    """Core song record — one row per unique audio file."""
    __tablename__ = "songs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    file_path: Mapped[str] = mapped_column(String(1024), unique=True, nullable=False, index=True)
    file_hash: Mapped[Optional[str]] = mapped_column(String(32), nullable=True, index=True)
    title: Mapped[str] = mapped_column(String(512), nullable=False)
    artist: Mapped[str] = mapped_column(String(512), nullable=False, default="Unknown Artist")
    album: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    duration_sec: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    # ML outputs
    predicted_genre: Mapped[Optional[str]] = mapped_column(String(128), nullable=True, index=True)
    genre_confidence: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    cluster_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, index=True)

    # Timestamps
    date_added: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Relationships
    audio_feature: Mapped[Optional["AudioFeature"]] = relationship(
        "AudioFeature", back_populates="song", uselist=False, cascade="all, delete-orphan"
    )
    listening_events: Mapped[List["ListeningEvent"]] = relationship(
        "ListeningEvent", back_populates="song", cascade="all, delete-orphan"
    )
    daily_recs: Mapped[List["DailyRecommendation"]] = relationship(
        "DailyRecommendation", back_populates="song", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Song id={self.id} title={self.title!r} artist={self.artist!r}>"


# ─── AudioFeature ─────────────────────────────────────────────────────────────

class AudioFeature(Base):
    """
    Librosa-derived feature vector for one song.
    JSON arrays are stored as TEXT and serialised/deserialised in Python.
    This keeps SQLite simple while still supporting the full feature set.
    """
    __tablename__ = "audio_features"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    song_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("songs.id", ondelete="CASCADE"), unique=True, nullable=False
    )

    # MFCC (40 coefficients) — stored as JSON strings
    mfcc_mean: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # JSON list[float] len=40
    mfcc_std: Mapped[Optional[str]] = mapped_column(Text, nullable=True)   # JSON list[float] len=40

    # Chroma (12 pitch classes)
    chroma_mean: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # JSON list[float] len=12
    chroma_std: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Scalar features
    tempo: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    spectral_centroid_mean: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    spectral_centroid_std: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    zcr_mean: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    zcr_std: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    spectral_rolloff_mean: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    rms_mean: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    # Estimated key and mode (from chroma)
    estimated_key: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)   # 0–11 semitone
    estimated_mode: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)  # 0=minor 1=major

    extracted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    song: Mapped["Song"] = relationship("Song", back_populates="audio_feature")

    # ── helpers for JSON columns ───────────────────────────────────────────────

    def get_mfcc_mean(self) -> list[float]:
        return json.loads(self.mfcc_mean) if self.mfcc_mean else []

    def get_mfcc_std(self) -> list[float]:
        return json.loads(self.mfcc_std) if self.mfcc_std else []

    def get_chroma_mean(self) -> list[float]:
        return json.loads(self.chroma_mean) if self.chroma_mean else []

    def get_chroma_std(self) -> list[float]:
        return json.loads(self.chroma_std) if self.chroma_std else []

    def __repr__(self) -> str:
        return f"<AudioFeature song_id={self.song_id} tempo={self.tempo}>"


# ─── ListeningEvent ───────────────────────────────────────────────────────────

class ListeningEvent(Base):
    """
    One row per discrete user interaction with a song.
    completion_ratio: 0.0–1.0 (fraction of track played before action).
    context_genre: the dominant genre of the session at event time.
    """
    __tablename__ = "listening_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    song_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("songs.id", ondelete="CASCADE"), nullable=False, index=True
    )
    event_type: Mapped[EventType] = mapped_column(Enum(EventType), nullable=False)
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, nullable=False, index=True
    )
    session_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)  # UUID string
    completion_ratio: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    context_genre: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)

    song: Mapped["Song"] = relationship("Song", back_populates="listening_events")

    def __repr__(self) -> str:
        return f"<ListeningEvent song_id={self.song_id} type={self.event_type} ts={self.timestamp}>"


# ─── UserPreference ───────────────────────────────────────────────────────────

class UserPreference(Base):
    """
    Aggregated genre preference score updated on every event.
    Score is not bounded — higher = stronger preference.
    """
    __tablename__ = "user_preferences"
    __table_args__ = (UniqueConstraint("genre", name="uq_genre"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    genre: Mapped[str] = mapped_column(String(128), nullable=False)
    score: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    play_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    skip_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow
    )

    def __repr__(self) -> str:
        return f"<UserPreference genre={self.genre!r} score={self.score:.2f}>"


# ─── DailyRecommendation ──────────────────────────────────────────────────────

class DailyRecommendation(Base):
    """
    Cached result of the daily recommendation run.
    Regenerated once per day (or on demand via /recommendations/refresh).
    """
    __tablename__ = "daily_recommendations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    rec_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    song_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("songs.id", ondelete="CASCADE"), nullable=False
    )
    rank: Mapped[int] = mapped_column(Integer, nullable=False)   # 1 = top pick
    reason_code: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    # e.g. "genre_match", "acoustic_similar", "not_played_recently"
    score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    generated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    song: Mapped["Song"] = relationship("Song", back_populates="daily_recs")

    def __repr__(self) -> str:
        return f"<DailyRecommendation date={self.rec_date} rank={self.rank} song_id={self.song_id}>"


# ─── WeekendPlaylist ──────────────────────────────────────────────────────────

class WeekendPlaylist(Base):
    """
    Generated weekend playlist — one row per week.
    song_ids stored as a JSON array (ordered).
    """
    __tablename__ = "weekend_playlists"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    week_start_date: Mapped[date] = mapped_column(Date, nullable=False, unique=True, index=True)
    song_ids_json: Mapped[str] = mapped_column(Text, nullable=False)   # JSON list[int]
    generated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    def get_song_ids(self) -> list[int]:
        return json.loads(self.song_ids_json)

    def set_song_ids(self, ids: list[int]) -> None:
        self.song_ids_json = json.dumps(ids)

    def __repr__(self) -> str:
        return f"<WeekendPlaylist week={self.week_start_date} count={len(self.get_song_ids())}>"
