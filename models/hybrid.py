"""
Hybrid recommendation engine.
Blends Content-Based + ALS Collaborative + LSTM Sequential scores.
Falls back gracefully:
  - 3-way (0.4 CB + 0.3 ALS + 0.3 LSTM) when all models available
  - 2-way (0.5 CB + 0.5 ALS) when LSTM unavailable
  - 1-way (CB only) when ALS also unavailable
"""
import logging
from pathlib import Path
from db import SessionLocal
from db.models import ListeningHistory, Song
from models.content_based import get_recommendations_for_user
from models.collaborative import get_als_recommendations, MIN_INTERACTIONS

logger = logging.getLogger(__name__)

# ── Blend weights (matching PLANNING.md) ─────────────────────────────────────
# 3-way blend
CB_WEIGHT_3WAY   = 0.4
ALS_WEIGHT_3WAY  = 0.3
LSTM_WEIGHT_3WAY = 0.3

# 2-way fallback
CB_WEIGHT_2WAY  = 0.5
ALS_WEIGHT_2WAY = 0.5

# 1-way fallback
CB_WEIGHT_ONLY  = 1.0

LSTM_MODEL_PATH = Path("models/saved/sequential_model.pt")


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


def _get_recent_song_ids(db, limit: int = 10) -> list[str]:
    """Get the most recently played song_ids for LSTM input."""
    results = (
        db.query(ListeningHistory.song_id)
        .order_by(ListeningHistory.played_at.desc())
        .limit(limit)
        .all()
    )
    # Reverse to chronological order
    return [r.song_id for r in reversed(results)]


def _has_enough_history(db) -> bool:
    count = db.query(ListeningHistory).count()
    return count >= MIN_INTERACTIONS


def _normalize(score_map: dict) -> dict:
    """Normalize scores to [0, 1] range."""
    if not score_map:
        return {}
    vals = list(score_map.values())
    min_v, max_v = min(vals), max(vals)
    if max_v == min_v:
        return {k: 1.0 for k in score_map}
    return {k: (v - min_v) / (max_v - min_v) for k, v in score_map.items()}


def get_hybrid_recommendations(top_n: int = 20) -> list[dict]:
    """
    Main hybrid recommendation function.
    Returns top_n recommended songs ranked by blended score.
    """
    db = SessionLocal()
    try:
        seed_songs = _get_seed_songs(db)
        use_als = _has_enough_history(db)
        use_lstm = LSTM_MODEL_PATH.exists()

        # ── Content-based scores ─────────────────────────────────────────
        cb_results = get_recommendations_for_user(
            top_n=top_n * 3,
            seed_song_ids=seed_songs if seed_songs else None,
        )
        cb_map = {r["song_id"]: r["score"] for r in cb_results}

        # ── Pure CB fallback ─────────────────────────────────────────────
        if not use_als and not use_lstm:
            logger.info("Using content-based only (no ALS or LSTM)")
            return sorted(cb_results, key=lambda x: x["score"], reverse=True)[:top_n]

        # ── ALS scores ───────────────────────────────────────────────────
        als_map = {}
        als_results = []
        if use_als:
            als_results = get_als_recommendations(top_n=top_n * 3)
            als_map = {r["song_id"]: r["score"] for r in als_results}

        # ── LSTM scores ──────────────────────────────────────────────────
        lstm_map = {}
        lstm_results = []
        if use_lstm:
            try:
                from models.sequential import predict_next_songs
                recent_ids = _get_recent_song_ids(db)
                lstm_results = predict_next_songs(recent_ids, top_n=top_n * 3)
                lstm_map = {r["song_id"]: r["score"] for r in lstm_results}
            except Exception as e:
                logger.warning(f"LSTM prediction failed, falling back: {e}")
                use_lstm = False

        # ── Determine blend weights ──────────────────────────────────────
        if use_als and use_lstm and lstm_map:
            cb_w, als_w, lstm_w = CB_WEIGHT_3WAY, ALS_WEIGHT_3WAY, LSTM_WEIGHT_3WAY
            blend_type = "3-way (CB+ALS+LSTM)"
        elif use_als:
            cb_w, als_w, lstm_w = CB_WEIGHT_2WAY, ALS_WEIGHT_2WAY, 0.0
            blend_type = "2-way (CB+ALS)"
        else:
            cb_w, als_w, lstm_w = CB_WEIGHT_ONLY, 0.0, 0.0
            blend_type = "1-way (CB only)"

        # ── Normalize all score maps ─────────────────────────────────────
        cb_norm = _normalize(cb_map)
        als_norm = _normalize(als_map)
        lstm_norm = _normalize(lstm_map)

        # ── Union of all candidate song_ids ──────────────────────────────
        all_sids = set(cb_norm.keys()) | set(als_norm.keys()) | set(lstm_norm.keys())

        # ── Blend scores ─────────────────────────────────────────────────
        blended = []
        all_results = cb_results + als_results + lstm_results
        for sid in all_sids:
            cb_score = cb_norm.get(sid, 0.0)
            als_score = als_norm.get(sid, 0.0)
            lstm_score = lstm_norm.get(sid, 0.0)
            final = (cb_w * cb_score) + (als_w * als_score) + (lstm_w * lstm_score)

            # Look up metadata from any result list
            meta = next(
                (r for r in all_results if r["song_id"] == sid),
                {"song_id": sid, "title": "Unknown", "artist": "Unknown", "genre": None}
            )
            blended.append({**meta, "score": round(final, 6)})

        blended.sort(key=lambda x: x["score"], reverse=True)
        top_candidates = blended[:top_n * 2]

        # ── Re-rank with bandit UCB scores ───────────────────────────────
        from models.bandit import rerank_with_bandit
        final = rerank_with_bandit(top_candidates, top_n=top_n)

        logger.info(
            f"Hybrid+Bandit [{blend_type}]: {len(final)} recommendations"
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
            candidates[0]
        )

        db.add(Recommendation(
            rec_type="daily",
            song_id=pick["song_id"],
            was_played=False,
        ))
        db.commit()

        logger.info(
            f"Daily recommendation: '{pick['title']}' "
            f"by {pick['artist']} (score: {pick['score']})"
        )
        return pick

    finally:
        db.close()
