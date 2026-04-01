import os
import logging
from dotenv import load_dotenv
from db import SessionLocal, check_db_connection
from data_collection.ingestion_pipeline import (
    run_local_ingestion, 
    run_playlist_ingestion, 
    run_ytmusic_ingestion
)

load_dotenv()
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s — %(message)s")
logger = logging.getLogger(__name__)

def main():
    logger.info("🎵 VibeFlow Ingestion Pipeline Starting...")

    if not check_db_connection():
        logger.error("❌ Cannot reach PostgreSQL. Is Docker running?")
        return

    db = SessionLocal()
    
    try:
        # 1. Local Library Ingestion
        music_dir = os.getenv("LOCAL_MUSIC_DIR", "./music_library")
        if os.path.exists(music_dir):
            res_local = run_local_ingestion(music_dir, db)
            logger.info(f"✅ Local Library: {res_local}")
        else:
            logger.warning(f"⚠️ LOCAL_MUSIC_DIR '{music_dir}' not found — skipping local scan")

        # 2. Playlist Ingestion
        playlist_dir = os.path.join(music_dir, "playlists") if os.path.exists(music_dir) else "./music_library/playlists"
        if os.path.exists(playlist_dir):
            res_playlists = run_playlist_ingestion(playlist_dir, db)
            logger.info(f"✅ Playlists: {res_playlists}")
        else:
            logger.warning(f"⚠️ Playlist dir '{playlist_dir}' not found — skipping playlist scan")

        # 3. YT Music Ingestion (Now using the Liked Songs fallback)
        auth_file = os.getenv("YTMUSIC_AUTH_FILE", "oauth.json")
        if os.path.exists(auth_file):
            try:
                res_yt = run_ytmusic_ingestion(db)
                logger.info(f"✅ YT Music: {res_yt}")
                
                # Retrain ALS now that we have real history injected
                from models.collaborative import train_als
                train_als()
            except Exception as e:
                logger.error(f"❌ YT Music ingestion failed: {e}")
        else:
            logger.warning("⚠️ oauth.json not found — run 'ytmusicapi oauth' first")

        logger.info("🎉 Ingestion complete!")

    finally:
        db.close()

if __name__ == "__main__":
    main()