"""
Hybrid recommendation engine.
Blends Content-Based + ALS Collaborative scores.
Falls back gracefully if ALS has insufficient data.
"""
import logging
from db import SessionLocal
from db.models import ListeningHistory, Song
from models.content_based import get_recommendations_for_user
from models.collaborative import get_als_recommendations, MIN_INTERACTIONS

logger = logging.getLogger(__name__)

# Blend weights — shift toward ALS as history grows
CONTENT_WEIGHT_DEFAULT  = 1.0   # Used when ALS unavailable
CONTENT_WEIGHT_WITH_ALS = 0.5
ALS_WEIGHT              = 0.5


def _get_seed_songs(db, limit: int = 30) -> list[str]:
    """Get top played songs to use as content-based seeds."""
    from sqlalchemy import func
    results = (
        db.query(ListeningHistory.song_id)
        .filter(ListeningHistory.skipped == False)
        .group_by(ListeningHistory.song_id)
        .order_by(func.count().desc())
        .limit(limit)
        .all()
    )
    return [r.song_id for r in results]


def _has_enough_history(db) -> bool:
    count = db.query(ListeningHistory).count()
    return count >= MIN_INTERACTIONS


def get_hybrid_recommendations(top_n: int = 20) -> list[dict]:
    """
    Main hybrid recommendation function.
    Returns top_n recommended songs ranked by blended score.
    """
    db = SessionLocal()
    try:
        seed_songs = _get_seed_songs(db)
        use_als    = _has_enough_history(db)

        # Content-based scores
        cb_results = get_recommendations_for_user(
            top_n=top_n * 3,
            seed_song_ids=seed_songs if seed_songs else None,
        )
        cb_map = {r["song_id"]: r["score"] for r in cb_results}

        if not use_als:
            logger.info("Using content-based only (not enough history for ALS)")
            return sorted(cb_results, key=lambda x: x["score"], reverse=True)[:top_n]

        # ALS scores
        als_results = get_als_recommendations(top_n=top_n * 3)
        als_map = {r["song_id"]: r["score"] for r in als_results}

        # Normalize scores to [0, 1] range
        def _normalize(score_map: dict) -> dict:
            if not score_map:
                return {}
            vals = list(score_map.values())
            min_v, max_v = min(vals), max(vals)
            if max_v == min_v:
                return {k: 1.0 for k in score_map}
            return {k: (v - min_v) / (max_v - min_v) for k, v in score_map.items()}

        cb_norm  = _normalize(cb_map)
        als_norm = _normalize(als_map)

        # Union of all candidate song_ids
        all_sids = set(cb_norm.keys()) | set(als_norm.keys())

        blended = []
        for sid in all_sids:
            cb_score  = cb_norm.get(sid, 0.0)
            als_score = als_norm.get(sid, 0.0)
            final     = (CONTENT_WEIGHT_WITH_ALS * cb_score) + (ALS_WEIGHT * als_score)

            # Look up metadata
            meta = next(
                (r for r in cb_results + als_results if r["song_id"] == sid),
                {"song_id": sid, "title": "Unknown", "artist": "Unknown", "genre": None}
            )
            blended.append({**meta, "score": round(final, 6)})

        blended.sort(key=lambda x: x["score"], reverse=True)
        top_candidates = blended[:top_n * 2]   # Get 2× for bandit to rerank

        # Re-rank with bandit UCB scores
        from models.bandit import rerank_with_bandit
        final = rerank_with_bandit(top_candidates, top_n=top_n)

        logger.info(
            f"Hybrid+Bandit: {len(final)} recommendations "
            f"(CB={'✅' if cb_norm else '❌'}, ALS={'✅' if als_norm else '❌'})"
        )
        return final

    finally:
        db.close()


def get_daily_recommendation() -> dict | None:
    """
    Pick the single best daily recommendation.
    Filters out songs recommended in the last 7 days.
    Falls back through progressively looser filters before returning None.
    """
    from datetime import datetime, timezone, timedelta
    from db.models import Recommendation

    db = SessionLocal()
    try:
        week_ago = datetime.now(timezone.utc) - timedelta(days=7)
        recent_rec_ids = {
            r.song_id for r in db.query(Recommendation)
            .filter(
                Recommendation.rec_type == "daily",
                Recommendation.recommended_at >= week_ago,
            ).all()
        }

        candidates = get_hybrid_recommendations(top_n=50)

        if not candidates:
            logger.error("Hybrid recommender returned 0 candidates — check library + features")
            return None

        # Pick first candidate not recently recommended
        pick = next(
            (c for c in candidates if c["song_id"] not in recent_rec_ids),
            candidates[0]  # All recently recommended? Just return the top pick
        )

        db.add(Recommendation(
            rec_type   = "daily",
            song_id    = pick["song_id"],
            was_played = False,
        ))
        db.commit()

        logger.info(
            f"Daily recommendation: '{pick['title']}' "
            f"by {pick['artist']} (score: {pick['score']})"
        )
        return pick

    finally:
        db.close()
