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
