"""
fetch_lyrics.py
---------------
Fetches Bleachers lyrics and writes them to public/data/songs.json.

Strategy:
  - Genius API  → album structure (which songs belong to which album)
  - lrclib.net  → actual lyrics (free, no auth, no scraping)

Genius's web scraping is now blocked (403), so we use lrclib.net for lyrics.
lrclib is a free, open-source lyrics database with full Bleachers coverage.

Run once (or whenever you want to sync new releases):
  cd scripts
  source .venv/bin/activate
  python fetch_lyrics.py

Requires a .env file with:
  GENIUS_ACCESS_TOKEN=your_token_here
"""

import os
import json
import re
import time
from pathlib import Path
import requests
from dotenv import load_dotenv

load_dotenv()

# ---------------------------------------------------------------------------
# Albums with their Genius album IDs (hardcoded for reliability).
# To add a new album: search genius.com for a song on that album, get its
# song ID from the API, then GET /songs/{id} to find the album ID.
# ---------------------------------------------------------------------------
ALBUMS = [
    {"name": "Strange Desire",                              "year": 2014, "genius_id": 108231},
    {"name": "Gone Now",                                    "year": 2017, "genius_id": 339923},
    {"name": "Take the Sadness Out of Saturday Night",      "year": 2021, "genius_id": 701041},
    # Genius indexes the 2024 self-titled album as the Deluxe edition
    {"name": "Bleachers",                                   "year": 2024, "genius_id": 1183217},
]

SECTION_HEADER_RE = re.compile(r'^\[.*\]$')
GENIUS_API = "https://api.genius.com"
LRCLIB_API = "https://lrclib.net/api"
OUTPUT_PATH = Path(__file__).parent.parent / "public" / "data" / "songs.json"


def clean_lyrics(raw: str) -> list[str]:
    """
    Turn a raw lyrics string into a list of clean lines.
    Strips section headers like [Verse 1], [Chorus], etc.
    Strips blank lines.
    """
    lines = []
    for line in raw.split("\n"):
        line = line.strip()
        if not line:
            continue
        if SECTION_HEADER_RE.match(line):
            continue
        lines.append(line)
    return lines


def get_album_tracks(headers: dict, album_id: int) -> list[dict]:
    """Fetch all tracks for a Genius album. Returns [{id, title}]."""
    resp = requests.get(f"{GENIUS_API}/albums/{album_id}/tracks", headers=headers)
    resp.raise_for_status()
    return [
        {"id": t["song"]["id"], "title": t["song"]["title"]}
        for t in resp.json()["response"]["tracks"]
    ]


def fetch_lyrics_from_lrclib(artist: str, title: str) -> list[str] | None:
    """
    Look up lyrics on lrclib.net.
    Returns a cleaned list of lines, or None if not found.

    lrclib is a free, open-source lyrics database.
    No API key needed. Rate limit is generous (no hard cap documented).
    """
    resp = requests.get(
        f"{LRCLIB_API}/search",
        params={"artist_name": artist, "track_name": title},
    )
    resp.raise_for_status()
    results = resp.json()

    if not results:
        return None

    # Take the first result (best match by lrclib's relevance ranking)
    plain_lyrics = results[0].get("plainLyrics")
    if not plain_lyrics:
        return None

    return clean_lyrics(plain_lyrics)


def main():
    token = os.environ.get("GENIUS_ACCESS_TOKEN")
    if not token:
        raise SystemExit(
            "ERROR: GENIUS_ACCESS_TOKEN not set.\n"
            "Copy scripts/.env.example to scripts/.env and add your token."
        )

    genius_headers = {"Authorization": f"Bearer {token}"}
    songs_output = []
    seen_titles: set[str] = set()

    for album_meta in ALBUMS:
        print(f"\nFetching: {album_meta['name']} ({album_meta['year']})")

        try:
            tracks = get_album_tracks(genius_headers, album_meta["genius_id"])
        except Exception as e:
            print(f"  WARNING: could not fetch album tracks from Genius — {e}")
            continue

        print(f"  {len(tracks)} tracks found via Genius API")

        for track in tracks:
            title = track["title"]
            canonical = title.lower().strip()

            if canonical in seen_titles:
                print(f"  SKIP (duplicate): {title}")
                continue
            seen_titles.add(canonical)

            lines = fetch_lyrics_from_lrclib("Bleachers", title)
            if lines is None:
                print(f"  SKIP (no lyrics on lrclib): {title}")
                continue

            songs_output.append({
                "id":    track["id"],
                "title": title,
                "album": album_meta["name"],
                "year":  album_meta["year"],
                "lines": lines,
            })
            print(f"  OK  {title} ({len(lines)} lines)")
            time.sleep(0.2)

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(songs_output, f, ensure_ascii=False, indent=2)

    print(f"\nDone. {len(songs_output)} songs written to {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
