"""
fetch_lyrics.py
---------------
Fetches Bleachers lyrics from the Genius API and writes them to
public/data/songs.json.

Run once (or whenever you want to sync new releases):
  cd scripts
  python fetch_lyrics.py

Requires a .env file in this directory with:
  GENIUS_ACCESS_TOKEN=your_token_here

Get a free token at https://genius.com/api-clients
"""

import os
import json
import re
import time
from pathlib import Path
from dotenv import load_dotenv
import lyricsgenius

load_dotenv()

# ---------------------------------------------------------------------------
# Album list — hardcoded so we control the canonical names and release order.
# If Bleachers releases a new album, add it here and re-run this script.
# ---------------------------------------------------------------------------
ALBUMS = [
    {"name": "Strange Desire",                              "year": 2014},
    {"name": "Gone Now",                                    "year": 2017},
    {"name": "Take the Sadness Out of Saturday Night",      "year": 2021},
    {"name": "Bleachers",                                   "year": 2024},
]

# Matches section headers like [Verse 1], [Chorus], [Bridge], etc.
SECTION_HEADER_RE = re.compile(r'^\[.*\]$')

OUTPUT_PATH = Path(__file__).parent.parent / "public" / "data" / "songs.json"


def clean_lyrics(raw: str) -> list[str]:
    """
    Turn a raw lyrics string into a list of clean lines.

    - Strips section headers ([Verse], [Chorus], etc.) — they're noise for search.
    - Strips leading/trailing whitespace from each line.
    - Drops empty lines.
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


def main():
    token = os.environ.get("GENIUS_ACCESS_TOKEN")
    if not token:
        raise SystemExit(
            "ERROR: GENIUS_ACCESS_TOKEN not set.\n"
            "Copy scripts/.env.example to scripts/.env and add your token."
        )

    genius = lyricsgenius.Genius(token)
    genius.verbose = False
    genius.remove_section_headers = False  # we handle cleaning ourselves

    songs_output = []
    seen_titles: set[str] = set()

    for album_meta in ALBUMS:
        print(f"\nFetching: {album_meta['name']} ({album_meta['year']})")
        album_obj = genius.search_album(album_meta["name"], "Bleachers")
        if album_obj is None:
            print(f"  WARNING: album not found on Genius — skipping")
            continue

        for track in album_obj.tracks:
            song = track.song
            canonical = song.title.lower().strip()

            # Skip if we've already seen a song with this title (e.g. live versions)
            if canonical in seen_titles:
                print(f"  SKIP (duplicate): {song.title}")
                continue
            seen_titles.add(canonical)

            if not song.lyrics:
                print(f"  SKIP (no lyrics): {song.title}")
                continue

            lines = clean_lyrics(song.lyrics)
            songs_output.append({
                "id":    song.id,
                "title": song.title,
                "album": album_meta["name"],
                "year":  album_meta["year"],
                "lines": lines,
            })
            print(f"  OK  {song.title} ({len(lines)} lines)")
            time.sleep(0.5)  # be polite to the API

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(songs_output, f, ensure_ascii=False, indent=2)

    print(f"\nDone. {len(songs_output)} songs written to {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
