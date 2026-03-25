from fastapi import APIRouter, HTTPException
from models.hybrid import get_daily_recommendation, get_hybrid_recommendations

router = APIRouter()


@router.get("/daily")
def daily_recommendation():
    result = get_daily_recommendation()
    if not result:
        raise HTTPException(status_code=404, detail="No recommendation available")
    return result


@router.get("/top")
def top_recommendations(n: int = 20):
    results = get_hybrid_recommendations(top_n=n)
    if not results:
        raise HTTPException(status_code=404, detail="No recommendations available")
    return {"recommendations": results, "count": len(results)}


@router.get("/weekend")
def weekend_playlist():
    from models.weekend_playlist import get_latest_weekend_playlist
    playlist = get_latest_weekend_playlist()
    if not playlist:
        raise HTTPException(status_code=404, detail="No weekend playlist generated yet")
    return {"playlist": playlist, "count": len(playlist)}

@router.get("/bandit/stats")
def bandit_stats(limit: int = 20):
    """Show which songs the bandit has learned most about."""
    from db import SessionLocal
    from db.models import BanditState, Song

    db = SessionLocal()
    try:
        states = (
            db.query(BanditState, Song)
            .join(Song, BanditState.song_id == Song.song_id)
            .filter((BanditState.play_count + BanditState.skip_count) > 0)
            .order_by(BanditState.total_reward.desc())
            .limit(limit)
            .all()
        )
        return {
            "learned_songs": [
                {
                    "title":        song.title,
                    "artist":       song.artist,
                    "plays":        state.play_count,
                    "skips":        state.skip_count,
                    "total_reward": round(state.total_reward, 3),
                }
                for state, song in states
            ]
        }
    finally:
        db.close()