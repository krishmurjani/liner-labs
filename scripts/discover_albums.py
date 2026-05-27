"""
discover_albums.py
------------------
Checks Genius for albums not yet in artists-config.json and adds them.

Usage:
  cd scripts
  source .venv/bin/activate
  python discover_albums.py

How it works:
  1. For each artist, looks up their Genius artist ID from the first album
     in their config (cached in genius_artist_id after the first run).
  2. Fetches the full album list from Genius (/artists/{id}/albums).
  3. Skips albums whose names match patterns in _skip_album_patterns
     (e.g. "karaoke", "deluxe edition") or whose IDs are in the
     artist's excluded_album_ids list.
  4. Appends genuinely new albums to the artist's album list.
  5. Saves the updated artists-config.json.

After running this, run fetch_lyrics.py --incremental for each affected
artist to fetch lyrics for the new albums.
"""

import json, os, time
from pathlib import Path
import requests
from dotenv import load_dotenv

load_dotenv()

CONFIG_PATH = Path(__file__).parent / "artists-config.json"
GENIUS_API  = "https://api.genius.com"
REQUEST_TIMEOUT = 30


def get_artist_id(headers: dict, album_id: int) -> int:
    r = requests.get(f"{GENIUS_API}/albums/{album_id}", headers=headers, timeout=REQUEST_TIMEOUT)
    r.raise_for_status()
    return r.json()["response"]["album"]["artist"]["id"]


def get_all_albums(headers: dict, artist_id: int) -> list[dict]:
    albums, page = [], 1
    while True:
        r = requests.get(
            f"{GENIUS_API}/artists/{artist_id}/albums",
            headers=headers,
            params={"page": page, "per_page": 20},
            timeout=REQUEST_TIMEOUT,
        )
        r.raise_for_status()
        data = r.json()["response"]
        albums.extend(data.get("albums", []))
        next_page = data.get("next_page")
        if not next_page:
            break
        page = next_page
        time.sleep(0.3)
    return albums


def main():
    token = os.environ.get("GENIUS_ACCESS_TOKEN")
    if not token:
        raise SystemExit("GENIUS_ACCESS_TOKEN not set in .env")
    headers = {"Authorization": f"Bearer {token}"}

    with open(CONFIG_PATH, encoding="utf-8") as f:
        config = json.load(f)

    skip_patterns = [p.lower() for p in config.get("_skip_album_patterns", [])]
    changed = False

    for slug, artist_data in config.items():
        if slug.startswith("_"):
            continue

        print(f"\n── {artist_data['name']} ──")

        # Resolve and cache the Genius artist ID
        if "genius_artist_id" not in artist_data:
            first_album_id = artist_data["albums"][0]["genius_id"]
            artist_id = get_artist_id(headers, first_album_id)
            artist_data["genius_artist_id"] = artist_id
            print(f"  Resolved artist ID: {artist_id}")
            changed = True
            time.sleep(0.3)
        else:
            artist_id = artist_data["genius_artist_id"]

        existing_ids  = {a["genius_id"] for a in artist_data["albums"]}
        excluded_ids  = set(artist_data.get("excluded_album_ids", []))

        all_genius_albums = get_all_albums(headers, artist_id)
        time.sleep(0.3)

        added = []
        for album in all_genius_albums:
            album_id   = album["id"]
            name       = album.get("name", "")
            name_lower = name.lower()

            if album_id in existing_ids:
                continue
            if album_id in excluded_ids:
                print(f"  SKIP (excluded):  {name}")
                continue
            if any(p in name_lower for p in skip_patterns):
                print(f"  SKIP (pattern):   {name}")
                continue

            rdc  = album.get("release_date_components") or {}
            year = rdc.get("year") or 0
            added.append({"name": name, "year": year, "genius_id": album_id})
            print(f"  NEW:              {name} ({year or '?'})")

        if added:
            artist_data["albums"].extend(added)
            changed = True
        else:
            print("  Up to date.")

    if changed:
        with open(CONFIG_PATH, "w", encoding="utf-8") as f:
            json.dump(config, f, ensure_ascii=False, indent=2)
        print("\nartists-config.json updated.")
    else:
        print("\nNo changes — all artists up to date.")


if __name__ == "__main__":
    main()
