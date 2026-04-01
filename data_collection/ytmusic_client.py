import os
import logging
from typing import Optional
from ytmusicapi import YTMusic
from ytmusicapi.auth.oauth.credentials import OAuthCredentials
from rapidfuzz import fuzz, process
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)


def get_ytmusic_client() -> Optional[YTMusic]:
    auth_file = os.getenv("YTMUSIC_AUTH_FILE", "oauth.json")
    client_id = os.getenv("YTMUSIC_CLIENT_ID")
    client_secret = os.getenv("YTMUSIC_CLIENT_SECRET")

    if os.path.exists(auth_file):
        if not client_id or not client_secret:
            logger.error("YTMUSIC_CLIENT_ID or YTMUSIC_CLIENT_SECRET missing from .env")
            return None
            
        logger.info(f"YT Music: authenticated via {auth_file} (OAuth)")
        credentials = OAuthCredentials(client_id=client_id, client_secret=client_secret)
        return YTMusic(auth_file, oauth_credentials=credentials)
        
    logger.warning(f"{auth_file} not found — run 'ytmusicapi oauth' first")
    return None


def fetch_liked_songs(yt: YTMusic, limit: int = 1000) -> list[dict]:
    all_songs = []
    try:
        results = yt.get_liked_songs(limit=limit)
        for track in results.get("tracks", []):
            parsed = _parse_yt_track(track)
            if parsed:
                all_songs.append(parsed)
    except Exception as e:
        logger.error(f"YT Music liked_songs error: {e}")
    logger.info(f"Fetched {len(all_songs)} liked songs from YT Music")
    return all_songs

def fetch_history(yt: YTMusic) -> list[dict]:
    # Known bug in ytmusicapi: get_history fails with OAuth (HTTP 400).
    # We log it and gracefully skip. The pipeline will rely on liked_songs.
    logger.warning("YT Music OAuth: get_history() endpoint failed (known bug). Skipping history.")
    return []


def map_yt_to_local(
    yt_songs: list[dict],
    local_songs: list[dict],
    threshold: int = 80,
) -> dict[str, Optional[str]]:
    """
    Map YT Music song IDs → local song_ids using fuzzy title+artist matching.
    Returns {yt_song_id: local_song_id or None}
    """
    choices = {
        s["song_id"]: f"{s['title']} {s['artist']}".lower()
        for s in local_songs
    }
    mapping = {}

    for yt_song in yt_songs:
        query = f"{yt_song['title']} {yt_song['artist']}".lower()
        result = process.extractOne(
            query,
            choices,
            scorer=fuzz.token_sort_ratio,
            score_cutoff=threshold,
        )
        mapping[yt_song["song_id"]] = result[2] if result else None

    matched = sum(1 for v in mapping.values() if v)
    logger.info(f"Mapped {matched}/{len(yt_songs)} YT Music songs to local library")
    return mapping


def _parse_yt_track(track: dict) -> Optional[dict]:
    if not track.get("videoId"):
        return None
    artists = track.get("artists") or []
    return {
        "song_id":    f"yt_{track['videoId']}",
        "title":      track.get("title", "Unknown"),
        "artist":     ", ".join(a.get("name", "") for a in artists),
        "album":      (track.get("album") or {}).get("name"),
        "duration_ms": _duration_to_ms(track.get("duration")),
        "source":     "ytmusic",
    }


def _duration_to_ms(duration_str: Optional[str]) -> Optional[int]:
    if not duration_str:
        return None
    try:
        parts = list(map(int, duration_str.split(":")))
        if len(parts) == 2:
            return (parts[0] * 60 + parts[1]) * 1000
        if len(parts) == 3:
            return (parts[0] * 3600 + parts[1] * 60 + parts[2]) * 1000
    except (ValueError, AttributeError):
        return None
    return None
