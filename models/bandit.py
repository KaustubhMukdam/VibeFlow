"""
LinUCB Bandit — contextual bandit for real-time recommendation re-ranking.

Each song has:
  a_matrix: d×d matrix (initialized to identity)
  b_vector: d×1 vector (initialized to zeros)

UCB score = θᵀx + α√(xᵀA⁻¹x)
  where θ = A⁻¹b (estimated reward weights)
        x = feature context vector for the song
        α = exploration parameter (higher = more exploration)
"""
import logging
import numpy as np
import json
from typing import Optional
from db import SessionLocal
from db.models import BanditState, Song, ListeningHistory

logger = logging.getLogger(__name__)

ALPHA = 0.3          # Exploration parameter — tune down as history grows
FEATURE_DIM = 19     # 6 audio features + 13 MFCC means = 19
REWARD_FULL_PLAY  =  1.0
REWARD_PARTIAL    =  0.3
REWARD_SKIP       = -0.5


def _build_context(song: Song) -> np.ndarray:
    """Build a normalized feature context vector for a song."""
    mfcc = song.mfcc_vector if isinstance(song.mfcc_vector, list) else [0.0] * 13
    mfcc_13 = (mfcc[:13] + [0.0] * 13)[:13]

    audio = [
        song.energy           or 0.0,
        (song.tempo or 120)   / 200.0,   # Normalize BPM to ~[0,1]
        song.acousticness     or 0.0,
        song.instrumentalness or 0.0,
        song.speechiness      or 0.0,
        min(1.0, max(0.0, (song.loudness or -20 + 60) / 60)),  # Normalize dB
    ]
    return np.array(audio + mfcc_13, dtype=np.float64)


def _get_or_init_bandit_state(db, song_id: str) -> BanditState:
    """Get existing bandit state or initialize for a new song."""
    state = db.query(BanditState).filter_by(song_id=song_id).first()
    if not state:
        A = np.eye(FEATURE_DIM).tolist()
        b = np.zeros(FEATURE_DIM).tolist()
        state = BanditState(
            song_id      = song_id,
            a_matrix     = A,
            b_vector     = b,
            play_count   = 0,
            skip_count   = 0,
            total_reward = 0.0,
        )
        db.add(state)
        db.flush()
    return state


def compute_ucb_score(song: Song, bandit_state: BanditState) -> float:
    """
    Compute LinUCB upper confidence bound score for a song.
    Higher score = more likely to be recommended.
    """
    x = _build_context(song)

    A = np.array(bandit_state.a_matrix, dtype=np.float64)
    b = np.array(bandit_state.b_vector, dtype=np.float64)

    try:
        A_inv = np.linalg.inv(A)
    except np.linalg.LinAlgError:
        A_inv = np.eye(FEATURE_DIM)

    theta = A_inv @ b
    exploitation = float(theta @ x)
    exploration  = float(ALPHA * np.sqrt(x @ A_inv @ x))
    return round(exploitation + exploration, 6)


def update_bandit(song_id: str, reward: float) -> None:
    """
    Update a_matrix and b_vector for a song after observing a reward.
    Call this every time a song finishes playing or is skipped.
    """
    db = SessionLocal()
    try:
        song  = db.query(Song).filter_by(song_id=song_id).first()
        if not song:
            logger.warning(f"Song {song_id} not found for bandit update")
            return

        state = _get_or_init_bandit_state(db, song_id)
        x     = _build_context(song)

        A = np.array(state.a_matrix, dtype=np.float64)
        b = np.array(state.b_vector, dtype=np.float64)

        # LinUCB update rule
        A += np.outer(x, x)
        b += reward * x

        state.a_matrix     = A.tolist()
        state.b_vector     = b.tolist()
        state.total_reward = (state.total_reward or 0.0) + reward

        if reward >= REWARD_PARTIAL:
            state.play_count = (state.play_count or 0) + 1
        else:
            state.skip_count = (state.skip_count or 0) + 1

        db.commit()
        logger.debug(f"Bandit updated: {song.title} | reward={reward:.2f}")

    except Exception as e:
        logger.error(f"Bandit update failed for {song_id}: {e}")
        db.rollback()
    finally:
        db.close()


def compute_reward(play_duration_ms: int, song_duration_ms: int, skipped: bool) -> float:
    """Convert play event into a scalar reward signal."""
    if skipped or song_duration_ms <= 0:
        return REWARD_SKIP

    completion = play_duration_ms / song_duration_ms
    if completion >= 0.80:
        return REWARD_FULL_PLAY
    elif completion >= 0.40:
        return REWARD_PARTIAL
    elif completion >= 0.15:
        return 0.1
    else:
        return REWARD_SKIP


def rerank_with_bandit(candidates: list[dict], top_n: int = 20) -> list[dict]:
    """
    Re-rank hybrid candidates using bandit UCB scores.
    Blends hybrid score (60%) with bandit UCB (40%).
    Falls back to hybrid ranking if bandit state unavailable.
    """
    if not candidates:
        return []

    db = SessionLocal()
    try:
        # Normalize hybrid scores to [0, 1]
        scores  = [c["score"] for c in candidates]
        min_s, max_s = min(scores), max(scores)
        score_range  = max_s - min_s if max_s != min_s else 1.0

        reranked = []
        for c in candidates:
            song = db.query(Song).filter_by(song_id=c["song_id"]).first()
            if not song:
                reranked.append({**c, "final_score": c["score"]})
                continue

            state       = db.query(BanditState).filter_by(song_id=c["song_id"]).first()
            hybrid_norm = (c["score"] - min_s) / score_range

            if state and (state.play_count or 0) + (state.skip_count or 0) > 0:
                ucb_score = compute_ucb_score(song, state)
                # Clip UCB to reasonable range and normalize
                ucb_norm  = min(1.0, max(0.0, (ucb_score + 1) / 2))
                final     = 0.6 * hybrid_norm + 0.4 * ucb_norm
            else:
                # No feedback yet — pure hybrid
                final = hybrid_norm

            reranked.append({**c, "final_score": round(final, 6)})

        reranked.sort(key=lambda x: x["final_score"], reverse=True)
        return reranked[:top_n]

    finally:
        db.close()


def select_next_songs(
    session_id: str,
    count: int = 3,
) -> list[dict]:
    """
    Bandit actively selects the next best songs for a session queue.
    Excludes songs already played in this session.
    Uses hybrid recommendations as candidates, then picks via UCB.

    This is the core "GET /session/{id}/next" feature from PLANNING.md.
    """
    db = SessionLocal()
    try:
        # Get songs already played in this session
        played = (
            db.query(ListeningHistory.song_id)
            .filter(ListeningHistory.session_id == session_id)
            .all()
        )
        played_ids = {p.song_id for p in played}

        # Get all candidate songs
        candidates = db.query(Song).filter(
            Song.source.in_(["local", "ytmusic_only"]),
            Song.mfcc_vector.isnot(None),
            ~Song.song_id.in_(played_ids) if played_ids else True,
        ).all()

        if not candidates:
            return []

        # Score each candidate with LinUCB
        scored = []
        for song in candidates:
            state = db.query(BanditState).filter_by(song_id=song.song_id).first()
            if state and (state.play_count or 0) + (state.skip_count or 0) > 0:
                ucb = compute_ucb_score(song, state)
            else:
                # Cold start — use exploration bonus only
                x = _build_context(song)
                ucb = float(ALPHA * np.sqrt(x @ x))  # Pure exploration

            scored.append({
                "song_id": song.song_id,
                "title":   song.title,
                "artist":  song.artist,
                "genre":   song.genre,
                "ucb_score": round(ucb, 6),
            })

        scored.sort(key=lambda x: x["ucb_score"], reverse=True)
        return scored[:count]

    except Exception as e:
        logger.error(f"select_next_songs failed: {e}", exc_info=True)
        return []
    finally:
        db.close()