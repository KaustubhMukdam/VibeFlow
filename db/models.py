from sqlalchemy import (
    Column, String, Integer, Float, Boolean,
    DateTime, Text, ForeignKey, CheckConstraint, Index
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import declarative_base, relationship
from sqlalchemy.sql import func

Base = declarative_base()


class Song(Base):
    __tablename__ = "songs"

    song_id             = Column(String(255), primary_key=True)
    title               = Column(String(500), nullable=False)
    artist              = Column(String(500), nullable=False)
    album               = Column(String(500))
    source              = Column(String(50))
    duration_ms         = Column(Integer)
    file_path           = Column(Text)
    genre               = Column(String(100))
    genre_confidence    = Column(Float)
    danceability        = Column(Float)
    energy              = Column(Float)
    valence             = Column(Float)
    tempo               = Column(Float)
    acousticness        = Column(Float)
    instrumentalness    = Column(Float)
    speechiness         = Column(Float)
    loudness            = Column(Float)
    mfcc_vector         = Column(JSONB)
    added_at            = Column(DateTime(timezone=True), server_default=func.now())
    updated_at          = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    history         = relationship("ListeningHistory", back_populates="song")
    bandit          = relationship("BanditState", back_populates="song", uselist=False)
    recommendations = relationship("Recommendation", back_populates="song")

    __table_args__ = (
        CheckConstraint(
            "source IN ('spotify','ytmusic','local','ytmusic_only')",
            name="ck_songs_source"
        ),
        Index("idx_songs_source", "source"),
        Index("idx_songs_genre", "genre"),
    )


class Session(Base):
    __tablename__ = "sessions"

    session_id     = Column(String(255), primary_key=True)
    started_at     = Column(DateTime(timezone=True), nullable=False)
    ended_at       = Column(DateTime(timezone=True))
    dominant_genre = Column(String(100))
    avg_energy     = Column(Float)
    song_count     = Column(Integer, default=0)
    skip_rate      = Column(Float, default=0.0)

    history = relationship("ListeningHistory", back_populates="session")


class ListeningHistory(Base):
    __tablename__ = "listening_history"

    id               = Column(Integer, primary_key=True, autoincrement=True)
    song_id          = Column(String(255), ForeignKey("songs.song_id", ondelete="CASCADE"))
    played_at        = Column(DateTime(timezone=True), nullable=False)
    play_duration_ms = Column(Integer)
    song_duration_ms = Column(Integer)
    skipped          = Column(Boolean, default=False)
    skip_time_ms     = Column(Integer)
    source           = Column(String(50))
    session_id       = Column(String(255), ForeignKey("sessions.session_id"))

    song    = relationship("Song", back_populates="history")
    session = relationship("Session", back_populates="history")

    __table_args__ = (
        Index("idx_history_played_at", "played_at"),
        Index("idx_history_song_id", "song_id"),
        Index("idx_history_session", "session_id"),
    )


class BanditState(Base):
    __tablename__ = "bandit_state"

    song_id      = Column(String(255), ForeignKey("songs.song_id", ondelete="CASCADE"), primary_key=True)
    A_matrix     = Column(JSONB, nullable=False)
    b_vector     = Column(JSONB, nullable=False)
    play_count   = Column(Integer, default=0)
    skip_count   = Column(Integer, default=0)
    total_reward = Column(Float, default=0.0)
    last_updated = Column(DateTime(timezone=True), server_default=func.now())

    song = relationship("Song", back_populates="bandit")


class Recommendation(Base):
    __tablename__ = "recommendations"

    id             = Column(Integer, primary_key=True, autoincrement=True)
    rec_type       = Column(String(50))
    song_id        = Column(String(255), ForeignKey("songs.song_id"))
    recommended_at = Column(DateTime(timezone=True), server_default=func.now())
    was_played     = Column(Boolean, default=False)
    user_rating    = Column(Integer)

    song = relationship("Song", back_populates="recommendations")

    __table_args__ = (
        CheckConstraint("rec_type IN ('daily','weekend','session')", name="ck_rec_type"),
        CheckConstraint("user_rating BETWEEN 1 AND 5", name="ck_user_rating"),
        Index("idx_recs_type_date", "rec_type", "recommended_at"),
    )


class Playlist(Base):
    __tablename__ = "playlists"

    id         = Column(Integer, primary_key=True, autoincrement=True)
    name       = Column(String(255), nullable=False, unique=True)
    source     = Column(String(50), default="local")  # 'local', 'ytmusic'
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    tracks = relationship("PlaylistTrack", back_populates="playlist")


class PlaylistTrack(Base):
    __tablename__ = "playlist_tracks"

    id          = Column(Integer, primary_key=True, autoincrement=True)
    playlist_id = Column(Integer, ForeignKey("playlists.id", ondelete="CASCADE"))
    song_id     = Column(String(255), ForeignKey("songs.song_id", ondelete="CASCADE"))
    position    = Column(Integer)

    playlist = relationship("Playlist", back_populates="tracks")
    song     = relationship("Song")

    __table_args__ = (
        Index("idx_playlist_tracks_pid", "playlist_id"),
    )
