"""
Run genre classification on all local songs in DB and write results back.
Usage: python -m models.genre_classifier.tag_library
"""
import logging
import sys
from db import SessionLocal
from db.models import Song
from models.genre_classifier.predict import predict_genre

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)


def tag_all_songs(force_retag: bool = False) -> dict:
    """
    Predict genre for every local song in DB that has a file_path.
    Skips already-tagged songs unless force_retag=True.
    """
    db = SessionLocal()
    try:
        query = db.query(Song).filter(Song.source == "local", Song.file_path.isnot(None))
        if not force_retag:
            query = query.filter(Song.genre.is_(None))

        songs = query.all()
        total = len(songs)
        logger.info(f"Tagging {total} songs with genre labels...")

        tagged = 0
        failed = 0

        for idx, song in enumerate(songs):
            try:
                result = predict_genre(song.file_path)
                if result:
                    song.genre            = result["vibeflow_genre"]
                    song.genre_confidence = result["confidence"]
                    tagged += 1
                    if idx % 50 == 0 and idx > 0:
                        db.commit()
                        logger.info(f"  [{idx}/{total}] Progress saved...")
                else:
                    failed += 1
            except Exception as e:
                logger.warning(f"Failed to tag {song.title}: {e}")
                failed += 1

        db.commit()
        logger.info(f"✅ Tagged {tagged} songs | Failed: {failed}")
        return {"tagged": tagged, "failed": failed, "total": total}

    finally:
        db.close()


def print_genre_distribution():
    """Print genre breakdown of the library after tagging."""
    db = SessionLocal()
    try:
        from sqlalchemy import func
        results = (
            db.query(Song.genre, func.count(Song.song_id).label("count"))
            .filter(Song.source == "local")
            .group_by(Song.genre)
            .order_by(func.count(Song.song_id).desc())
            .all()
        )
        print("\n🎵 VibeFlow Library — Genre Distribution")
        print("=" * 40)
        total = sum(r.count for r in results)
        for row in results:
            genre = row.genre or "Untagged"
            pct   = (row.count / total) * 100 if total else 0
            bar   = "█" * int(pct / 2)
            print(f"  {genre:<22} {row.count:>4} songs  {pct:>5.1f}%  {bar}")
        print(f"{'─'*40}")
        print(f"  {'Total':<22} {total:>4} songs")
    finally:
        db.close()


if __name__ == "__main__":
    force = "--force" in sys.argv
    result = tag_all_songs(force_retag=force)
    print_genre_distribution()
