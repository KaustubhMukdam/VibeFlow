"""
app/db/repository.py
Thin async data-access layer. All raw DB queries live here —
route handlers and services call these functions, never SQLAlchemy directly.
"""
from __future__ import annotations

import json
from datetime import date, datetime, timedelta, timezone
from typing import Optional

from sqlalchemy import delete, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.models import (
    AudioFeature,
    DailyRecommendation,
    EventType,
    ListeningEvent,
    Song,
    UserPreference,
    WeekendPlaylist,
)


# ─── Song Repository ──────────────────────────────────────────────────────────

class SongRepo:

    @staticmethod
    async def get_by_id(db: AsyncSession, song_id: int) -> Optional[Song]:
        result = await db.execute(
            select(Song).where(Song.id == song_id, Song.is_active == True)
            .options(selectinload(Song.audio_feature))
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def get_by_path(db: AsyncSession, file_path: str) -> Optional[Song]:
        result = await db.execute(
            select(Song).where(Song.file_path == file_path)
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def get_all_active(db: AsyncSession) -> list[Song]:
        result = await db.execute(
            select(Song)
            .where(Song.is_active == True)
            .order_by(Song.title)
            .options(selectinload(Song.audio_feature))
        )
        return list(result.scalars().all())

    @staticmethod
    async def get_paginated(
        db: AsyncSession,
        page: int = 1,
        page_size: int = 50,
        genre: Optional[str] = None,
        artist: Optional[str] = None,
        search: Optional[str] = None,
    ) -> tuple[list[Song], int]:
        q = select(Song).where(Song.is_active == True)
        if genre:
            q = q.where(Song.predicted_genre == genre)
        if artist:
            q = q.where(Song.artist.ilike(f"%{artist}%"))
        if search:
            q = q.where(
                Song.title.ilike(f"%{search}%") | Song.artist.ilike(f"%{search}%")
            )
        count_q = select(func.count()).select_from(q.subquery())
        total: int = (await db.execute(count_q)).scalar_one()
        songs_q = (
            q.order_by(Song.title)
            .offset((page - 1) * page_size)
            .limit(page_size)
            .options(selectinload(Song.audio_feature))  # eager-load to avoid async lazy-load crash
        )
        songs = list((await db.execute(songs_q)).scalars().all())
        return songs, total

    @staticmethod
    async def upsert(db: AsyncSession, song: Song) -> Song:
        """Insert or update a song record by file_path."""
        existing = await SongRepo.get_by_path(db, song.file_path)
        if existing:
            existing.title = song.title
            existing.artist = song.artist
            existing.album = song.album
            existing.duration_sec = song.duration_sec
            existing.file_hash = song.file_hash
            await db.flush()
            return existing
        db.add(song)
        await db.flush()
        return song

    @staticmethod
    async def update_genre(
        db: AsyncSession,
        song_id: int,
        genre: str,
        confidence: Optional[float] = None,
        cluster_id: Optional[int] = None,
    ) -> None:
        await db.execute(
            update(Song)
            .where(Song.id == song_id)
            .values(
                predicted_genre=genre,
                genre_confidence=confidence,
                cluster_id=cluster_id,
            )
        )

    @staticmethod
    async def count(db: AsyncSession) -> int:
        result = await db.execute(select(func.count()).select_from(Song).where(Song.is_active == True))
        return result.scalar_one()

    @staticmethod
    async def get_songs_without_features(db: AsyncSession) -> list[Song]:
        """Return songs that have no AudioFeature row yet."""
        result = await db.execute(
            select(Song)
            .outerjoin(AudioFeature, Song.id == AudioFeature.song_id)
            .where(Song.is_active == True, AudioFeature.id == None)
        )
        return list(result.scalars().all())

    @staticmethod
    async def get_all_ids(db: AsyncSession) -> list[int]:
        result = await db.execute(select(Song.id).where(Song.is_active == True))
        return list(result.scalars().all())

    @staticmethod
    async def get_distinct_genres(db: AsyncSession) -> list[str]:
        result = await db.execute(
            select(Song.predicted_genre)
            .where(Song.predicted_genre != None, Song.is_active == True)
            .distinct()
        )
        return [r for r in result.scalars().all() if r]


# ─── Feature Repository ───────────────────────────────────────────────────────

class FeatureRepo:

    @staticmethod
    async def get_by_song_id(db: AsyncSession, song_id: int) -> Optional[AudioFeature]:
        result = await db.execute(
            select(AudioFeature).where(AudioFeature.song_id == song_id)
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def upsert(db: AsyncSession, feature: AudioFeature) -> AudioFeature:
        existing = await FeatureRepo.get_by_song_id(db, feature.song_id)
        if existing:
            existing.mfcc_mean = feature.mfcc_mean
            existing.mfcc_std = feature.mfcc_std
            existing.chroma_mean = feature.chroma_mean
            existing.chroma_std = feature.chroma_std
            existing.tempo = feature.tempo
            existing.spectral_centroid_mean = feature.spectral_centroid_mean
            existing.spectral_centroid_std = feature.spectral_centroid_std
            existing.zcr_mean = feature.zcr_mean
            existing.zcr_std = feature.zcr_std
            existing.spectral_rolloff_mean = feature.spectral_rolloff_mean
            existing.rms_mean = feature.rms_mean
            existing.estimated_key = feature.estimated_key
            existing.estimated_mode = feature.estimated_mode
            existing.extracted_at = feature.extracted_at
            await db.flush()
            return existing
        db.add(feature)
        await db.flush()
        return feature

    @staticmethod
    async def get_all(db: AsyncSession) -> list[AudioFeature]:
        result = await db.execute(
            select(AudioFeature).join(Song, Song.id == AudioFeature.song_id)
            .where(Song.is_active == True)
        )
        return list(result.scalars().all())

    @staticmethod
    async def count_extracted(db: AsyncSession) -> int:
        result = await db.execute(select(func.count()).select_from(AudioFeature))
        return result.scalar_one()


# ─── Event Repository ─────────────────────────────────────────────────────────

class EventRepo:

    @staticmethod
    async def log(db: AsyncSession, event: ListeningEvent) -> ListeningEvent:
        db.add(event)
        await db.flush()
        return event

    @staticmethod
    async def get_history(
        db: AsyncSession,
        page: int = 1,
        page_size: int = 50,
        song_id: Optional[int] = None,
    ) -> tuple[list[ListeningEvent], int]:
        q = select(ListeningEvent)
        if song_id:
            q = q.where(ListeningEvent.song_id == song_id)
        count_q = select(func.count()).select_from(q.subquery())
        total: int = (await db.execute(count_q)).scalar_one()
        history_q = (
            q.order_by(ListeningEvent.timestamp.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        events = list((await db.execute(history_q)).scalars().all())
        return events, total

    @staticmethod
    async def get_recent_events(
        db: AsyncSession, hours: int = 24
    ) -> list[ListeningEvent]:
        since = datetime.now(timezone.utc) - timedelta(hours=hours)
        result = await db.execute(
            select(ListeningEvent)
            .where(ListeningEvent.timestamp >= since)
            .order_by(ListeningEvent.timestamp.desc())
        )
        return list(result.scalars().all())

    @staticmethod
    async def get_song_events(
        db: AsyncSession, song_id: int
    ) -> list[ListeningEvent]:
        result = await db.execute(
            select(ListeningEvent)
            .where(ListeningEvent.song_id == song_id)
            .order_by(ListeningEvent.timestamp.desc())
        )
        return list(result.scalars().all())

    @staticmethod
    async def get_session_events(
        db: AsyncSession, session_id: str
    ) -> list[ListeningEvent]:
        result = await db.execute(
            select(ListeningEvent)
            .where(ListeningEvent.session_id == session_id)
            .order_by(ListeningEvent.timestamp.asc())
        )
        return list(result.scalars().all())

    @staticmethod
    async def count(db: AsyncSession) -> int:
        result = await db.execute(select(func.count()).select_from(ListeningEvent))
        return result.scalar_one()


# ─── Preference Repository ────────────────────────────────────────────────────

class PreferenceRepo:

    @staticmethod
    async def get_all(db: AsyncSession) -> list[UserPreference]:
        result = await db.execute(
            select(UserPreference).order_by(UserPreference.score.desc())
        )
        return list(result.scalars().all())

    @staticmethod
    async def get_by_genre(db: AsyncSession, genre: str) -> Optional[UserPreference]:
        result = await db.execute(
            select(UserPreference).where(UserPreference.genre == genre)
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def upsert_genre_score(
        db: AsyncSession,
        genre: str,
        score_delta: float,
        event_type: EventType,
    ) -> None:
        """Atomically update a genre's preference score."""
        existing = await PreferenceRepo.get_by_genre(db, genre)
        if existing:
            existing.score += score_delta
            existing.updated_at = datetime.now(timezone.utc)
            if event_type in (EventType.PLAY, EventType.COMPLETE, EventType.REPLAY):
                existing.play_count += 1
            elif event_type == EventType.SKIP:
                existing.skip_count += 1
        else:
            pref = UserPreference(
                genre=genre,
                score=score_delta,
                play_count=1 if event_type != EventType.SKIP else 0,
                skip_count=1 if event_type == EventType.SKIP else 0,
            )
            db.add(pref)
        await db.flush()


# ─── Recommendation Repositories ──────────────────────────────────────────────

class RecommendationRepo:

    @staticmethod
    async def get_daily(db: AsyncSession, rec_date: date) -> list[DailyRecommendation]:
        result = await db.execute(
            select(DailyRecommendation)
            .where(DailyRecommendation.rec_date == rec_date)
            .order_by(DailyRecommendation.rank)
            .options(selectinload(DailyRecommendation.song))
        )
        return list(result.scalars().all())

    @staticmethod
    async def save_daily(
        db: AsyncSession, rec_date: date, recs: list[dict]
    ) -> None:
        """Replace today's recommendations atomically."""
        await db.execute(
            delete(DailyRecommendation).where(DailyRecommendation.rec_date == rec_date)
        )
        for rec in recs:
            payload = {"rec_date": rec_date, **rec}
            db.add(DailyRecommendation(**payload))
        await db.flush()

    @staticmethod
    async def get_weekend_playlist(
        db: AsyncSession, week_start: date
    ) -> Optional[WeekendPlaylist]:
        result = await db.execute(
            select(WeekendPlaylist).where(WeekendPlaylist.week_start_date == week_start)
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def save_weekend_playlist(
        db: AsyncSession, week_start: date, song_ids: list[int]
    ) -> WeekendPlaylist:
        existing = await RecommendationRepo.get_weekend_playlist(db, week_start)
        if existing:
            existing.set_song_ids(song_ids)
            existing.generated_at = datetime.now(timezone.utc)
            await db.flush()
            return existing
        playlist = WeekendPlaylist(week_start_date=week_start)
        playlist.set_song_ids(song_ids)
        db.add(playlist)
        await db.flush()
        return playlist
