import os
from fastapi import APIRouter, BackgroundTasks
from db import SessionLocal
from db.models import Song
from sqlalchemy import func

router = APIRouter()


@router.get("/genres")
def genre_distribution():
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


@router.get("/stats")
def library_stats():
    db = SessionLocal()
    try:
        total_songs   = db.query(Song).filter(Song.source == "local").count()
        tagged_songs  = db.query(Song).filter(
            Song.source == "local", Song.genre.isnot(None)
        ).count()
        total_playlists = db.query(func.count()).select_from(
            __import__("db.models", fromlist=["Playlist"]).Playlist
        ).scalar()
        return {
            "total_songs":    total_songs,
            "tagged_songs":   tagged_songs,
            "total_playlists": total_playlists,
        }
    finally:
        db.close()


@router.post("/scan")
def trigger_scan(background_tasks: BackgroundTasks):
    def _scan():
        import os
        from data_collection.ingestion_pipeline import run_local_ingestion
        from db import SessionLocal as DB
        db = DB()
        try:
            run_local_ingestion(os.getenv("LOCAL_MUSIC_DIR", "./music_library"), db)
        finally:
            db.close()

    background_tasks.add_task(_scan)
    return {"message": "Library scan started in background"}
