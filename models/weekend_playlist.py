"""
Weekend Playlist Generator.
Builds a ~20 song playlist optimized for Friday/Saturday evening listening.
Strategy: Higher energy + danceability + genre diversity vs daily recommendations.
"""
import logging
from datetime import datetime, timezone
from db import SessionLocal
from db.models import Song, Recommendation, BanditState
from models.hybrid import get_hybrid_recommendations

logger = logging.getLogger(__name__)

WEEKEND_GENRES_PRIORITY = [
    "HipHop_Punjabi",
    "Electronic_Dance",
    "Pop",
    "Folk_Country",
    "RnB_Soul",
    "Rock_Metal",
    "Instrumental",
]

WEEKEND_TARGET_SIZE = 20


def generate_weekend_playlist() -> list[dict]:
    """
    Generate a weekend playlist:
    1. Get hybrid recommendations (large pool)
    2. Boost high-energy songs
    3. Enforce genre diversity (max 40% from any one genre)
    4. Save to recommendations table with rec_type='weekend'
    """
    db = SessionLocal()
    try:
        # Get a large candidate pool
        candidates = get_hybrid_recommendations(top_n=100)
        if not candidates:
            logger.warning("No candidates for weekend playlist")
            return []

        # Enrich with energy data from DB
        enriched = []
        for c in candidates:
            song = db.query(Song).filter_by(song_id=c["song_id"]).first()
            if not song:
                continue
            energy = song.energy or 0.0
            tempo  = (song.tempo or 100) / 200.0

            # Weekend score: upweight energy + tempo
            weekend_score = (
                c.get("final_score", c["score"]) * 0.5 +
                energy * 0.3 +
                tempo  * 0.2
            )
            enriched.append({**c, "weekend_score": round(weekend_score, 6), "energy": energy})

        enriched.sort(key=lambda x: x["weekend_score"], reverse=True)

        # Genre diversity enforcement
        genre_counts = {}
        max_per_genre = int(WEEKEND_TARGET_SIZE * 0.40)   # Max 40% per genre
        playlist = []

        for track in enriched:
            genre = track.get("genre") or "Unknown"
            count = genre_counts.get(genre, 0)
            if count >= max_per_genre:
                continue
            genre_counts[genre] = count + 1
            playlist.append(track)
            if len(playlist) >= WEEKEND_TARGET_SIZE:
                break

        # If diversity filter left us short, fill with remaining top tracks
        if len(playlist) < WEEKEND_TARGET_SIZE:
            used_ids = {t["song_id"] for t in playlist}
            for track in enriched:
                if track["song_id"] not in used_ids:
                    playlist.append(track)
                    if len(playlist) >= WEEKEND_TARGET_SIZE:
                        break

        # Save to recommendations table
        for track in playlist:
            db.add(Recommendation(
                rec_type   = "weekend",
                song_id    = track["song_id"],
                was_played = False,
            ))
        db.commit()

        logger.info(f"Weekend playlist generated: {len(playlist)} songs")
        _log_playlist(playlist)
        return playlist

    finally:
        db.close()


def get_latest_weekend_playlist() -> list[dict]:
    """
    Return the most recently generated weekend playlist from the DB.
    Falls back to generating a new one if none exists.
    """
    from datetime import timedelta
    db = SessionLocal()
    try:
        week_ago = datetime.now(timezone.utc) - timedelta(days=7)
        recent = (
            db.query(Recommendation)
            .filter(
                Recommendation.rec_type       == "weekend",
                Recommendation.recommended_at >= week_ago,
            )
            .order_by(Recommendation.recommended_at.desc())
            .all()
        )

        if not recent:
            logger.info("No recent weekend playlist found — generating new one")
            return generate_weekend_playlist()

        results = []
        for rec in recent:
            song = db.query(Song).filter_by(song_id=rec.song_id).first()
            if song:
                results.append({
                    "song_id":    song.song_id,
                    "title":      song.title,
                    "artist":     song.artist,
                    "genre":      song.genre,
                    "was_played": rec.was_played,
                })
        return results

    finally:
        db.close()


def _log_playlist(playlist: list[dict]):
    logger.info("\n🎵 Weekend Playlist:")
    logger.info("=" * 50)
    for i, track in enumerate(playlist, 1):
        logger.info(
            f"  {i:>2}. {track['title']:<35} "
            f"{track.get('artist',''):<25} "
            f"[{track.get('genre','?')}]"
        )