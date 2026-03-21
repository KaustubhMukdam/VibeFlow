import logging
from pathlib import Path
from typing import Optional
from rapidfuzz import fuzz, process
import re

logger = logging.getLogger(__name__)


def parse_m3u(file_path: str) -> list[dict]:
    """Parse M3U/M3U8 file. Returns list of track entry dicts."""
    entries = []
    current_meta = {}

    with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
        lines = f.readlines()

    for line in lines:
        line = line.strip()
        if not line or line == "#EXTM3U":
            continue
        if line.startswith("#EXTINF:"):
            try:
                meta_part = line[len("#EXTINF:"):]
                duration_str, display_name = meta_part.split(",", 1)
                current_meta = {
                    "duration_s":    int(float(duration_str)),
                    "display_name":  display_name.strip(),
                }
            except (ValueError, IndexError):
                current_meta = {}
        elif not line.startswith("#"):
            entries.append({
                "file_path":    line,
                "title":        current_meta.get("display_name") or Path(line).stem,
                "duration_s":   current_meta.get("duration_s"),
            })
            current_meta = {}

    logger.info(f"Parsed {len(entries)} tracks from {Path(file_path).name}")
    return entries


def scan_playlists(playlist_dir: str) -> dict[str, list[dict]]:
    """Scan a directory for all M3U/M3U8 files. Returns {name: [entries]}."""
    playlists = {}
    playlist_path = Path(playlist_dir)

    if not playlist_path.exists():
        logger.warning(f"Playlist directory not found: {playlist_dir}")
        return playlists

    seen = set()
    for f in playlist_path.iterdir():
        if f.suffix.lower() in (".m3u", ".m3u8") and f.stem not in seen:
            seen.add(f.stem)
            playlists[f.stem] = parse_m3u(str(f))

    logger.info(f"Found {len(playlists)} playlists in {playlist_dir}")
    return playlists



def _clean_title(raw: str) -> str:
    """
    Strip common download-site suffixes and noise from filenames/titles
    so fuzzy matching works across differently-named copies of the same song.
    """
    noise_patterns = [
        r"\(SPOTISAVER\)", r"\(SpotiDown\.App\)", r"\(SpotifyMate\.com\)",
        r"SpotiDown\.App\s*-\s*", r"SpotifyMate\.com\s*-\s*",
        r"\(DJJOhAL\.Com\)", r"DJJOhAL\.Com\s*", r"Djjohal\.fm\s*",
        r"\(Raag\.Fm\)", r"\(PenduJatt\.Com\.Se\)", r"\(Mr-Jat\.in\)",
        r"\(KoshalWorld\.Com\)", r"\(SambalpuriStar\.In\)",
        r"\b128\s*Kbps\b", r"\b320\s*Kbps\b", r"\b192\s*Kbps\b",
        r"- Lofi$", r"- Slowed & Reverb$", r"- Slowed\+Reverb$",
        r"- sped up$", r"- Remix$", r"- Unplugged$",
        r"\s*\(feat\..*?\)", r"\s*feat\..*?$",
        r"\s*From -.*?-", r"\s*From _.*?_",
        r"_\d+$",  # trailing version numbers like _1
    ]
    result = raw
    for pattern in noise_patterns:
        result = re.sub(pattern, "", result, flags=re.IGNORECASE)
    return result.strip(" -_").strip()


def match_entries_to_songs(
    entries: list[dict],
    db_songs: list[dict],
    threshold: int = 70,   # Lowered from 75 for better coverage
) -> list:
    """
    Fuzzy-match each M3U entry to a DB song_id.
    Handles Samsung Music full phone paths + cleans download-site noise.
    Returns list of song_ids (None where unmatched).
    """
    if not db_songs:
        return [None] * len(entries)

    # Build cleaned lookup: song_id → cleaned title
    choices = {
        s["song_id"]: _clean_title(s["title"]).lower()
        for s in db_songs
    }

    matched_ids = []
    for entry in entries:
        # Extract just the filename stem from full phone paths
        raw_path = entry.get("file_path", "")
        raw_title = entry.get("title", "")

        # Samsung Music stores full paths: /storage/emulated/0/Music/Song.mp3
        stem_from_path = Path(raw_path).stem if raw_path else ""

        # Try both the display_name and the path stem, pick best match
        candidates = [raw_title, stem_from_path]
        best_match = None
        best_score = 0

        for candidate in candidates:
            if not candidate:
                continue
            cleaned = _clean_title(candidate).lower()
            result = process.extractOne(
                cleaned,
                choices,
                scorer=fuzz.token_sort_ratio,
                score_cutoff=threshold,
            )
            if result and result[1] > best_score:
                best_score = result[1]
                best_match = result[2]

        matched_ids.append(best_match)

    matched = sum(1 for x in matched_ids if x is not None)
    logger.info(f"Matched {matched}/{len(entries)} playlist entries to songs in DB")
    return matched_ids