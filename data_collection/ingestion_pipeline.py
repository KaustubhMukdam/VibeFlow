import os
import logging
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from sqlalchemy.dialects.postgresql import insert as pg_insert
from db.models import Song, ListeningHistory, Playlist, PlaylistTrack
from db import SessionLocal
from typing import Optional

logger = logging.getLogger(__name__)


def upsert_songs(songs: list[dict], db: Session) -> int:
    if not songs:
        return 0
    count = 0
    for song in songs:
        try:
            stmt = pg_insert(Song).values(
                song_id          = song["song_id"],
                title            = song.get("title", "Unknown"),
                artist           = song.get("artist", "Unknown Artist"),
                album            = song.get("album"),
                source           = song.get("source"),
                duration_ms      = song.get("duration_ms"),
                file_path        = song.get("file_path"),
                genre            = song.get("genre"),
                genre_confidence = song.get("genre_confidence"),
                danceability     = song.get("danceability"),
                energy           = song.get("energy"),
                valence          = song.get("valence"),
                tempo            = song.get("tempo"),
                acousticness     = song.get("acousticness"),
                instrumentalness = song.get("instrumentalness"),
                speechiness      = song.get("speechiness"),
                loudness         = song.get("loudness"),
                mfcc_vector      = song.get("mfcc_vector"),
            ).on_conflict_do_update(
                index_elements=["song_id"],
                set_={
                    "title":            song.get("title", "Unknown"),
                    "artist":           song.get("artist", "Unknown Artist"),
                    "energy":           song.get("energy"),
                    "tempo":            song.get("tempo"),
                    "loudness":         song.get("loudness"),
                    "mfcc_vector":      song.get("mfcc_vector"),
                    "updated_at":       datetime.now(timezone.utc),
                }
            )
            db.execute(stmt)
            count += 1
        except Exception as e:
            logger.error(f"Failed upsert for {song.get('song_id')}: {e}")
            db.rollback()
    db.commit()
    logger.info(f"Upserted {count} songs")
    return count


def insert_listening_history(records: list[dict], db: Session) -> int:
    if not records:
        return 0
    count = 0
    for record in records:
        try:
            played_at = record.get("played_at")
            if isinstance(played_at, str):
                played_at = datetime.fromisoformat(played_at.replace("Z", "+00:00"))
            if not played_at:
                continue

            exists = db.query(ListeningHistory).filter_by(
                song_id=record["song_id"],
                played_at=played_at,
            ).first()
            if exists:
                continue

            db.add(ListeningHistory(
                song_id          = record["song_id"],
                played_at        = played_at,
                play_duration_ms = record.get("play_duration_ms"),
                song_duration_ms = record.get("song_duration_ms"),
                skipped          = record.get("skipped", False),
                skip_time_ms     = record.get("skip_time_ms"),
                source           = record.get("source"),
                session_id       = record.get("session_id"),
            ))
            count += 1
        except Exception as e:
            logger.error(f"History insert failed: {e}")
            db.rollback()
    db.commit()
    logger.info(f"Inserted {count} history records")
    return count


def upsert_playlists(
    playlists: dict[str, list[dict]],
    song_id_matches: dict[str, list],
    db: Session,
) -> dict:
    from sqlalchemy.dialects.postgresql import insert as pg_insert

    playlists_added = 0
    tracks_added = 0

    for name, entries in playlists.items():
        try:
            # Upsert playlist row
            stmt = pg_insert(Playlist).values(name=name, source="local")
            stmt = stmt.on_conflict_do_nothing(index_elements=["name"])
            db.execute(stmt)
            db.flush()

            pl = db.query(Playlist).filter_by(name=name).first()
            if not pl:
                continue
            if pl.id and db.query(PlaylistTrack).filter_by(playlist_id=pl.id).count() == 0:
                playlists_added += 1

            matched_ids = song_id_matches.get(name, [])
            for pos, song_id in enumerate(matched_ids):
                if not song_id:
                    continue
                # ON CONFLICT DO NOTHING — safe to call multiple times
                track_stmt = pg_insert(PlaylistTrack).values(
                    playlist_id=pl.id,
                    song_id=song_id,
                    position=pos,
                )
                track_stmt = track_stmt.on_conflict_do_nothing(
                    index_elements=["playlist_id", "song_id"]
                )
                result = db.execute(track_stmt)
                if result.rowcount:
                    tracks_added += 1

            db.commit()

        except Exception as e:
            logger.error(f"Playlist upsert failed for '{name}': {e}")
            db.rollback()
            continue

    logger.info(f"Processed {len(playlists)} playlists, added {tracks_added} tracks")
    return {"playlists": playlists_added, "tracks": tracks_added}



def run_local_ingestion(music_dir: str, db: Session) -> dict:
    from data_collection.local_scanner import scan_library
    logger.info("=== Local Library Ingestion ===")
    songs = scan_library(music_dir)
    count = upsert_songs(songs, db)
    return {"songs_upserted": count}


def run_playlist_ingestion(playlist_dir: str, db: Session) -> dict:
    from data_collection.playlist_parser import scan_playlists, match_entries_to_songs
    logger.info("=== Playlist Ingestion ===")

    playlists = scan_playlists(playlist_dir)
    if not playlists:
        logger.warning("No playlists found.")
        return {"playlists": 0, "tracks": 0}

    db_songs = [
        {"song_id": s.song_id, "title": s.title, "artist": s.artist}
        for s in db.query(Song).filter(Song.source == "local").all()
    ]

    song_id_matches = {
        name: match_entries_to_songs(entries, db_songs)
        for name, entries in playlists.items()
    }

    return upsert_playlists(playlists, song_id_matches, db)


def run_ytmusic_ingestion(db: Session) -> dict:
    from data_collection.ytmusic_client import (
        get_ytmusic_client, fetch_liked_songs,
        fetch_history, map_yt_to_local,
    )
    logger.info("=== YT Music Ingestion ===")

    yt = get_ytmusic_client()
    liked   = fetch_liked_songs(yt)
    history = fetch_history(yt)

    all_yt_songs = {s["song_id"]: s for s in liked + history}

    local_songs = [
        {"song_id": s.song_id, "title": s.title, "artist": s.artist}
        for s in db.query(Song).filter(Song.source == "local").all()
    ]
    mapping = map_yt_to_local(list(all_yt_songs.values()), local_songs)

    songs_to_insert = []
    for yt_id, yt_song in all_yt_songs.items():
        local_id = mapping.get(yt_id)
        if not local_id:
            yt_song["source"] = "ytmusic_only"
            songs_to_insert.append(yt_song)

    songs_count   = upsert_songs(songs_to_insert, db)
    history_count = insert_listening_history(
        [{"song_id": mapping.get(s["song_id"], s["song_id"]),
          "source": "ytmusic", **s}
         for s in history],
        db,
    )
    return {"songs_upserted": songs_count, "history_inserted": history_count}
