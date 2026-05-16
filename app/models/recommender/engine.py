"""
app/models/recommender/engine.py
The main recommendation engine — combines all three scoring layers:

  1. Behavior scoring   (play/skip/complete history with time decay)
  2. Similarity scoring (cosine distance to recently liked songs)
  3. Genre reranking    (boost preferred genres, diversify playlist)

Exposes two public functions:
  - recommend_daily(db, n)        → daily top-N picks
  - generate_weekend_playlist(db) → diversity-aware weekend playlist
"""
from __future__ import annotations

from datetime import date, datetime, timezone

import structlog

from app.core.config import get_settings
from app.db.models import EventType
from app.db.repository import (
    EventRepo,
    PreferenceRepo,
    RecommendationRepo,
    SongRepo,
)
from app.db.session import AsyncSession
from app.models.recommender.behavior import get_behavior_scores, get_recently_liked_songs
from app.models.recommender.genre_reranker import apply_diversity_rules, rerank_by_genre
from app.models.recommender.similarity import get_similar_to_many, is_matrix_ready
from app.services.events.preference_scorer import compute_genre_preference_scores

log = structlog.get_logger(__name__)


# ─── Reason codes ─────────────────────────────────────────────────────────────

REASON_GENRE_MATCH = "genre_match"
REASON_ACOUSTIC_SIMILAR = "acoustic_similar"
REASON_NOT_PLAYED_RECENTLY = "not_played_recently"
REASON_DISCOVERY = "discovery"
REASON_HIGH_REPLAY = "high_replay"


# ─── Daily recommendations ────────────────────────────────────────────────────

async def recommend_daily(
    db: AsyncSession,
    n: int | None = None,
    force_refresh: bool = False,
) -> list[dict]:
    """
    Generate today's personalised top-N recommendations.

    Returns a list of dicts:
      {song_id, rank, reason_code, score, rec_date}

    On subsequent calls for the same day, returns the cached result unless
    force_refresh=True.
    """
    settings = get_settings()
    n = n or settings.DAILY_RECOMMENDATION_COUNT
    today = date.today()

    # Return cached result if available
    if not force_refresh:
        cached = await RecommendationRepo.get_daily(db, today)
        if cached:
            log.info("engine.daily.cache_hit", date=str(today), count=len(cached))
            return [
                {
                    "song_id": r.song_id,
                    "rank": r.rank,
                    "reason_code": r.reason_code,
                    "score": r.score,
                    "rec_date": r.rec_date,
                    "song": r.song,
                }
                for r in cached
            ]

    log.info("engine.daily.generating", date=str(today), n=n)

    # 1. Get all active songs
    all_songs = await SongRepo.get_all_active(db)
    all_song_ids = [s.id for s in all_songs]

    if not all_song_ids:
        return []

    song_genre_map = {s.id: s.predicted_genre for s in all_songs}
    song_artist_map = {s.id: s.artist for s in all_songs}

    # 2. Get songs played in last 24h to exclude from recommendations
    recent_events = await EventRepo.get_recent_events(db, hours=24)
    recently_played_ids = {e.song_id for e in recent_events}
    candidates = [sid for sid in all_song_ids if sid not in recently_played_ids]

    if len(candidates) < n:
        # Not enough fresh candidates — include some recently played
        candidates = all_song_ids

    # 3. Behavior scores
    behavior_scores = await get_behavior_scores(
        candidates, db, half_life_days=settings.BEHAVIOR_DECAY_HALF_LIFE_DAYS
    )

    # 4. Similarity scores from recently liked songs
    liked_seeds = await get_recently_liked_songs(db, hours=72, top_k=10)
    similarity_pairs: list[tuple[int, float]] = []
    if liked_seeds and is_matrix_ready():
        similarity_pairs = get_similar_to_many(
            liked_seeds, top_k=n * 3, exclude_ids=recently_played_ids
        )
        sim_score_map = dict(similarity_pairs)
    else:
        sim_score_map = {}

    # 5. Merge scores
    candidate_scores: list[tuple[int, float]] = []
    for song_id in candidates:
        b_score = behavior_scores.get(song_id, 0.0)
        s_score = sim_score_map.get(song_id, 0.0) * 2.0  # similarity has higher weight
        total = b_score + s_score
        candidate_scores.append((song_id, total))

    # 6. Genre preference reranking
    genre_prefs = await compute_genre_preference_scores(db)
    unheard_ids = {s.id for s in all_songs if s.id not in behavior_scores or behavior_scores[s.id] == 0}

    reranked = rerank_by_genre(
        candidate_scores,
        song_genre_map,
        genre_prefs,
        unheard_song_ids=unheard_ids,
    )

    # 7. Pick top-N
    top_n = reranked[:n]

    # 8. Assign reason codes
    def _reason(song_id: int, base_score: float) -> str:
        if song_id in {s for s, _ in similarity_pairs[:5]}:
            return REASON_ACOUSTIC_SIMILAR
        g = song_genre_map.get(song_id)
        if g and genre_prefs.get(g, 0) > 0.2:
            return REASON_GENRE_MATCH
        if song_id in unheard_ids:
            return REASON_DISCOVERY
        if song_id not in recently_played_ids:
            return REASON_NOT_PLAYED_RECENTLY
        return REASON_GENRE_MATCH

    recs = [
        {
            "song_id": sid,
            "rank": rank + 1,
            "reason_code": _reason(sid, score),
            "score": round(score, 4),
            "rec_date": today,
        }
        for rank, (sid, score) in enumerate(top_n)
    ]

    # 9. Cache in DB
    await RecommendationRepo.save_daily(db, today, recs)
    log.info("engine.daily.done", count=len(recs))
    return recs


# ─── Weekend playlist ─────────────────────────────────────────────────────────

async def generate_weekend_playlist(
    db: AsyncSession,
    n: int | None = None,
    force_refresh: bool = False,
) -> list[int]:
    """
    Generate a diversity-aware weekend playlist.

    Rules:
    - At least 3 genres represented.
    - No more than 3 consecutive songs from the same genre.
    - No more than 2 consecutive songs from the same artist.
    - At least 15% songs the user hasn't played yet (discovery).
    """
    settings = get_settings()
    n = n or settings.WEEKEND_PLAYLIST_COUNT

    # Find this week's Monday as the cache key
    today = date.today()
    week_start = today  # simplified: use today as the key for current weekend

    if not force_refresh:
        cached = await RecommendationRepo.get_weekend_playlist(db, week_start)
        if cached:
            log.info("engine.weekend.cache_hit", week_start=str(week_start))
            return cached.get_song_ids()

    log.info("engine.weekend.generating", n=n)

    all_songs = await SongRepo.get_all_active(db)
    all_song_ids = [s.id for s in all_songs]
    song_genre_map = {s.id: s.predicted_genre for s in all_songs}
    song_artist_map = {s.id: s.artist for s in all_songs}

    # Score candidates (larger pool than daily)
    behavior_scores = await get_behavior_scores(
        all_song_ids, db, half_life_days=settings.BEHAVIOR_DECAY_HALF_LIFE_DAYS
    )
    genre_prefs = await compute_genre_preference_scores(db)

    liked_seeds = await get_recently_liked_songs(db, hours=7 * 24, top_k=15)
    if liked_seeds and is_matrix_ready():
        sim_pairs = get_similar_to_many(liked_seeds, top_k=n * 2)
        sim_score_map = dict(sim_pairs)
    else:
        sim_score_map = {}

    unheard_ids = {s.id for s in all_songs if behavior_scores.get(s.id, 0) == 0}

    candidate_scores = [
        (sid, behavior_scores.get(sid, 0.0) + sim_score_map.get(sid, 0.0) * 1.5)
        for sid in all_song_ids
    ]

    reranked = rerank_by_genre(
        candidate_scores,
        song_genre_map,
        genre_prefs,
        unheard_song_ids=unheard_ids,
        unheard_bonus=1.0,  # stronger discovery push for weekends
    )

    # Apply diversity rules
    diverse_ids = apply_diversity_rules(
        reranked[:n * 2],
        song_genre_map,
        song_artist_map,
    )

    playlist_ids = diverse_ids[:n]

    await RecommendationRepo.save_weekend_playlist(db, week_start, playlist_ids)
    log.info("engine.weekend.done", count=len(playlist_ids))
    return playlist_ids
