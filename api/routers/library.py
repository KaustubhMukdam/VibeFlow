"""
Library routes — genre distribution, stats, taste profile, history,
and library scan trigger.
"""
import os
from fastapi import APIRouter, BackgroundTasks, Query
from db import SessionLocal
from db.models import Song, Playlist, ListeningHistory, Session
from sqlalchemy import func, desc, case

router = APIRouter()


# ── GET /genres ──────────────────────────────────────────────────────────────
@router.get("/genres")
def genre_distribution():
    """Get genre breakdown of the local music library."""
    db = SessionLocal()
    try:
        results = (
            db.query(Song.genre, func.count(Song.song_id).label("count"))
            .filter(Song.source == "local")
            .group_by(Song.genre)
            .order_by(func.count(Song.song_id).desc())
            .all()
        )
        total = sum(r.count for r in results)
        return {
            "genres": [
                {
                    "genre":      r.genre or "Untagged",
                    "count":      r.count,
                    "percentage": round((r.count / total) * 100, 1) if total else 0,
                }
                for r in results
            ],
            "total": total,
        }
    finally:
        db.close()


# ── GET /stats ───────────────────────────────────────────────────────────────
@router.get("/stats")
def library_stats():
    """Get high-level library statistics."""
    db = SessionLocal()
    try:
        total_songs = db.query(Song).filter(Song.source == "local").count()
        tagged_songs = db.query(Song).filter(
            Song.source == "local", Song.genre.isnot(None)
        ).count()
        total_playlists = db.query(func.count(Playlist.id)).scalar() or 0
        return {
            "total_songs":     total_songs,
            "tagged_songs":    tagged_songs,
            "total_playlists": total_playlists,
        }
    finally:
        db.close()


# ── GET /taste-profile ───────────────────────────────────────────────────────
@router.get("/taste-profile")
def taste_profile():
    """
    Returns aggregated audio features for the radar chart on the Taste Profile page.
    Computes weighted averages based on play frequency (more played = more weight).

    Features returned: energy, valence, tempo, acousticness,
                       instrumentalness, speechiness, danceability
    """
    db = SessionLocal()
    try:
        # Get play counts per song to weight the averages
        play_counts = (
            db.query(
                ListeningHistory.song_id,
                func.count().label("plays"),
            )
            .filter(ListeningHistory.skipped == False)
            .group_by(ListeningHistory.song_id)
            .subquery()
        )

        # Join with song features
        results = (
            db.query(
                func.sum(play_counts.c.plays).label("total_plays"),
                func.sum(Song.energy * play_counts.c.plays).label("energy_sum"),
                func.sum(Song.valence * play_counts.c.plays).label("valence_sum"),
                func.sum(Song.tempo * play_counts.c.plays).label("tempo_sum"),
                func.sum(Song.acousticness * play_counts.c.plays).label("acousticness_sum"),
                func.sum(Song.instrumentalness * play_counts.c.plays).label("instrumentalness_sum"),
                func.sum(Song.speechiness * play_counts.c.plays).label("speechiness_sum"),
                func.sum(Song.danceability * play_counts.c.plays).label("danceability_sum"),
                func.avg(Song.tempo).label("avg_tempo_raw"),
            )
            .join(Song, Song.song_id == play_counts.c.song_id)
            .first()
        )

        if not results or not results.total_plays:
            # Fallback: average across library if no history
            lib_avg = db.query(
                func.avg(Song.energy).label("energy"),
                func.avg(Song.valence).label("valence"),
                func.avg(Song.tempo).label("tempo"),
                func.avg(Song.acousticness).label("acousticness"),
                func.avg(Song.instrumentalness).label("instrumentalness"),
                func.avg(Song.speechiness).label("speechiness"),
                func.avg(Song.danceability).label("danceability"),
            ).filter(Song.source == "local").first()

            avg_tempo = float(lib_avg.tempo or 120)
            return {
                "features": {
                    "energy": round(float(lib_avg.energy or 0.5), 3),
                    "valence": round(float(lib_avg.valence or 0.5), 3),
                    "tempo": round(min(1.0, avg_tempo / 200.0), 3),
                    "acousticness": round(float(lib_avg.acousticness or 0.5), 3),
                    "instrumentalness": round(float(lib_avg.instrumentalness or 0.5), 3),
                    "speechiness": round(float(lib_avg.speechiness or 0.5), 3),
                    "danceability": round(float(lib_avg.danceability or 0.5), 3),
                },
                "avg_bpm": round(avg_tempo),
                "source": "library_average",
            }

        total = float(results.total_plays)
        avg_tempo = float(results.avg_tempo_raw or 120)

        # Determine dominant mood (simplified heuristic)
        energy_avg = float(results.energy_sum or 0) / total
        valence_avg = float(results.valence_sum or 0) / total

        if energy_avg > 0.7:
            dominant_mood = "Energetic"
        elif valence_avg > 0.6:
            dominant_mood = "Upbeat"
        elif energy_avg < 0.3:
            dominant_mood = "Calm"
        elif valence_avg < 0.3:
            dominant_mood = "Melancholic"
        else:
            dominant_mood = "Balanced"

        # Determine vibe type based on feature combinations
        tempo_norm = min(1.0, avg_tempo / 200.0)
        danceability_avg = float(results.danceability_sum or 0) / total
        instrumentalness_avg = float(results.instrumentalness_sum or 0) / total

        if danceability_avg > 0.6 and energy_avg > 0.6:
            vibe_type = "Dance Machine"
        elif instrumentalness_avg > 0.5:
            vibe_type = "Instrumental Explorer"
        elif energy_avg > 0.7:
            vibe_type = "Bass Head"
        elif valence_avg > 0.6 and energy_avg > 0.5:
            vibe_type = "Electronic Explorer"
        elif energy_avg < 0.4 and valence_avg < 0.4:
            vibe_type = "Night Owl"
        else:
            vibe_type = "Eclectic Listener"

        return {
            "features": {
                "energy": round(energy_avg, 3),
                "valence": round(valence_avg, 3),
                "tempo": round(tempo_norm, 3),
                "acousticness": round(float(results.acousticness_sum or 0) / total, 3),
                "instrumentalness": round(instrumentalness_avg, 3),
                "speechiness": round(float(results.speechiness_sum or 0) / total, 3),
                "danceability": round(danceability_avg, 3),
            },
            "avg_bpm": round(avg_tempo),
            "dominant_mood": dominant_mood,
            "vibe_type": vibe_type,
            "total_plays": int(total),
            "source": "weighted_history",
        }
    finally:
        db.close()


# ── GET /history ─────────────────────────────────────────────────────────────
@router.get("/history")
def listening_history(limit: int = Query(default=50, ge=1, le=200)):
    """
    Returns recent listening history with song metadata.
    Used by the Listening History page's "Recent Plays" table.
    """
    db = SessionLocal()
    try:
        results = (
            db.query(ListeningHistory, Song)
            .join(Song, ListeningHistory.song_id == Song.song_id)
            .order_by(ListeningHistory.played_at.desc())
            .limit(limit)
            .all()
        )

        # Overall stats
        total_plays = db.query(func.count(ListeningHistory.id)).scalar() or 0
        total_skips = (
            db.query(func.count(ListeningHistory.id))
            .filter(ListeningHistory.skipped == True)
            .scalar() or 0
        )
        skip_rate = round((total_skips / total_plays * 100), 1) if total_plays > 0 else 0

        # Most played genre
        top_genre = (
            db.query(Song.genre, func.count().label("cnt"))
            .join(ListeningHistory, ListeningHistory.song_id == Song.song_id)
            .filter(Song.genre.isnot(None))
            .group_by(Song.genre)
            .order_by(desc("cnt"))
            .first()
        )

        # Average session length
        avg_session = (
            db.query(func.avg(Session.song_count))
            .filter(Session.song_count.isnot(None), Session.song_count > 0)
            .scalar()
        )

        # Activity heatmap (7 days × 24 hours)
        from sqlalchemy import extract
        heatmap_data = (
            db.query(
                extract("dow", ListeningHistory.played_at).label("day_of_week"),
                extract("hour", ListeningHistory.played_at).label("hour"),
                func.count().label("play_count"),
            )
            .group_by("day_of_week", "hour")
            .all()
        )

        # Build 7×24 grid
        heatmap = [[0] * 24 for _ in range(7)]
        max_plays = 1
        for row in heatmap_data:
            dow = int(row.day_of_week)  # 0=Sunday in Postgres
            hour = int(row.hour)
            count = int(row.play_count)
            heatmap[dow][hour] = count
            if count > max_plays:
                max_plays = count

        return {
            "stats": {
                "total_plays": total_plays,
                "skip_rate": skip_rate,
                "most_played_genre": top_genre.genre if top_genre else "N/A",
                "avg_session_length": round(float(avg_session or 0)),
            },
            "heatmap": {
                "grid": heatmap,
                "max_plays": max_plays,
            },
            "recent_plays": [
                {
                    "song_id": h.song_id,
                    "title": song.title,
                    "artist": song.artist,
                    "genre": song.genre,
                    "played_at": h.played_at.isoformat() if h.played_at else None,
                    "play_duration_ms": h.play_duration_ms,
                    "skipped": h.skipped,
                }
                for h, song in results
            ],
        }
    finally:
        db.close()


# ── POST /scan ───────────────────────────────────────────────────────────────
@router.post("/scan")
def trigger_scan(background_tasks: BackgroundTasks):
    """Trigger a background library rescan."""
    def _scan():
        from data_collection.ingestion_pipeline import run_local_ingestion
        from db import SessionLocal as DB
        db = DB()
        try:
            music_dir = os.getenv("LOCAL_MUSIC_DIR", "./music_library")
            run_local_ingestion(music_dir, db)
        finally:
            db.close()

    background_tasks.add_task(_scan)
    return {"message": "Library scan started in background"}
