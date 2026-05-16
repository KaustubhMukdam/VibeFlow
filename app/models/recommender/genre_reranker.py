"""
app/models/recommender/genre_reranker.py
Genre-aware reranker.

Takes a scored candidate list and boosts songs matching the user's
top preferred genres. This is the layer that implements the
"smart genre shuffle" USP — songs in your favourite genre at this
moment float to the top of the recommendation list.
"""
from __future__ import annotations

import structlog

log = structlog.get_logger(__name__)


def rerank_by_genre(
    candidates: list[tuple[int, float]],   # (song_id, base_score)
    song_genre_map: dict[int, str | None],  # song_id → genre
    genre_preference_scores: dict[str, float],  # genre → preference_score
    genre_boost: float = 2.0,
    unheard_bonus: float = 0.5,
    unheard_song_ids: set[int] | None = None,
) -> list[tuple[int, float]]:
    """
    Apply genre preference boosting to a scored candidate list.

    Args:
        candidates:               (song_id, base_score) pairs.
        song_genre_map:           Maps each song_id to its genre label (or None).
        genre_preference_scores:  Normalised genre preference scores (0–1).
        genre_boost:              Multiplier applied to the genre preference score
                                  (additive to base_score).
        unheard_bonus:            Small bonus for songs never played before.
        unheard_song_ids:         Set of song IDs the user has never played.

    Returns:
        Re-ranked list of (song_id, adjusted_score) pairs, sorted descending.
    """
    unheard = unheard_song_ids or set()
    reranked: list[tuple[int, float]] = []

    for song_id, base_score in candidates:
        genre = song_genre_map.get(song_id)
        genre_score = genre_preference_scores.get(genre, 0.0) if genre else 0.0
        discovery_bonus = unheard_bonus if song_id in unheard else 0.0
        adjusted = base_score + genre_boost * genre_score + discovery_bonus
        reranked.append((song_id, adjusted))

    reranked.sort(key=lambda x: x[1], reverse=True)
    return reranked


def apply_diversity_rules(
    ranked: list[tuple[int, float]],
    song_genre_map: dict[int, str | None],
    song_artist_map: dict[int, str],
    max_consecutive_same_genre: int = 3,
    max_consecutive_same_artist: int = 2,
) -> list[int]:
    """
    Shuffle the playlist to avoid repetitive genre/artist runs.
    Uses a greedy interleaving approach.

    Returns:
        Reordered list of song_ids.
    """
    remaining = list(ranked)
    result: list[int] = []
    recent_genres: list[str | None] = []
    recent_artists: list[str] = []

    while remaining:
        placed = False
        for i, (song_id, _) in enumerate(remaining):
            genre = song_genre_map.get(song_id)
            artist = song_artist_map.get(song_id, "")

            genre_ok = (
                len(recent_genres) < max_consecutive_same_genre
                or genre != recent_genres[-1]
            )
            artist_ok = (
                len(recent_artists) < max_consecutive_same_artist
                or artist != recent_artists[-1]
            )

            if genre_ok and artist_ok:
                result.append(song_id)
                recent_genres.append(genre)
                recent_artists.append(artist)
                if len(recent_genres) > max_consecutive_same_genre:
                    recent_genres.pop(0)
                if len(recent_artists) > max_consecutive_same_artist:
                    recent_artists.pop(0)
                remaining.pop(i)
                placed = True
                break

        if not placed:
            # Fallback: no song satisfies constraints → just take the next best
            song_id, _ = remaining.pop(0)
            result.append(song_id)

    return result
