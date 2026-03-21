import logging
import os
from dotenv import load_dotenv
from db import SessionLocal, check_db_connection
from data_collection.ingestion_pipeline import (
    run_local_ingestion,
    run_playlist_ingestion,
    run_ytmusic_ingestion,
)

load_dotenv()
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
)
logger = logging.getLogger(__name__)


def main():
    logger.info("🎵 VibeFlow Ingestion Pipeline Starting...")

    if not check_db_connection():
        logger.error("❌ Cannot reach PostgreSQL. Is Docker running?")
        return

    db = SessionLocal()
    try:
        # 1. Local Library
        music_dir = os.getenv("LOCAL_MUSIC_DIR", "./music_library")
        if os.path.exists(music_dir):
            result = run_local_ingestion(music_dir, db)
            logger.info(f"✅ Local Library: {result}")
        else:
            logger.warning(f"⚠️  LOCAL_MUSIC_DIR '{music_dir}' not found — skipping")

        # 2. Playlists
        playlist_dir = os.getenv("PLAYLIST_DIR", "./music_library/playlists")
        if os.path.exists(playlist_dir):
            result = run_playlist_ingestion(playlist_dir, db)
            logger.info(f"✅ Playlists: {result}")
        else:
            logger.warning(f"⚠️  PLAYLIST_DIR '{playlist_dir}' not found — skipping")

        # 3. YT Music
        yt_auth = os.getenv("YTMUSIC_AUTH_FILE", "ytmusic_auth.json")
        if os.path.exists(yt_auth):
            result = run_ytmusic_ingestion(db)
            logger.info(f"✅ YT Music: {result}")
        else:
            logger.warning("⚠️  ytmusic_auth.json not found — run 'ytmusicapi browser' first")

        logger.info("🎉 Ingestion complete!")

    except Exception as e:
        logger.error(f"Pipeline failed: {e}", exc_info=True)
    finally:
        db.close()


if __name__ == "__main__":
    main()
