"""
fetch_lyrics.py
---------------
Fetches lyrics for a given artist and writes to public/data/{slug}/songs.json.

Usage:
  cd scripts
  source .venv/bin/activate
  python fetch_lyrics.py --slug bleachers
  python fetch_lyrics.py --slug taylor-swift

Strategy:
  - Genius API  → album structure + cover art (authenticated)
  - lrclib.net  → lyrics (free, no auth needed)

Album entry fields:
  name        - display name shown in the app
  year        - release year
  genius_id   - Genius album ID
  is_demo     - (optional) if True, overrides album name to "Voice Memos & Demos"
  art_override - (optional) URL to use instead of Genius album art

individual_songs entry fields:
  genius_id     - Genius song ID
  title         - song title
  album         - display album name
  year          - release year
  search_artist - (optional) artist name to use for lrclib search (defaults to artist name)
"""

import os, json, re, time, argparse
from pathlib import Path
import requests
import lyricsgenius as lg
from dotenv import load_dotenv

load_dotenv()

NON_ALBUM_COLLABS_NAME = "Non-album Singles & Collaborations"

# ---------------------------------------------------------------------------
# Artist catalogue — edit scripts/artists-config.json to add artists/albums.
# ---------------------------------------------------------------------------
_CONFIG_PATH = Path(__file__).parent / "artists-config.json"
with open(_CONFIG_PATH, encoding="utf-8") as _f:
    ARTISTS = json.load(_f)

GENIUS_API = "https://api.genius.com"
LRCLIB_API = "https://lrclib.net/api"
SECTION_RE = re.compile(r'^\[.*\]$')
DEMO_ALBUM_NAME = "Voice Memos & Demos"
LONG_POND_ART_URL = "https://is1-ssl.mzstatic.com/image/thumb/Music114/v4/0f/a0/14/0fa0144d-6cd5-792a-1589-3e1f0c25db49/20UM1IM08851.rgb.jpg/600x600bb.jpg"
REQUEST_TIMEOUT = 30
# Skip commentary/interview versions — these are not unique songs
SKIP_PATTERNS = {
    "commentary",
    "track by track",
}


def resolve_album_art(default_art: str, title: str) -> str:
    if "long pond studio sessions" in title.lower():
        return LONG_POND_ART_URL
    return default_art


def clean_lyrics(raw: str) -> list[str]:
    lines = []
    for line in raw.split("\n"):
        line = line.strip()
        if not line or SECTION_RE.match(line):
            continue
        lines.append(line)
    return lines


def get_album_info(headers: dict, album_id: int) -> dict:
    r = requests.get(f"{GENIUS_API}/albums/{album_id}", headers=headers, timeout=REQUEST_TIMEOUT)
    r.raise_for_status()
    album = r.json()["response"]["album"]
    art_url = album.get("cover_art_url", "")

    r2 = requests.get(f"{GENIUS_API}/albums/{album_id}/tracks", headers=headers, timeout=REQUEST_TIMEOUT)
    r2.raise_for_status()
    tracks = [{"id": t["song"]["id"], "title": t["song"]["title"]}
              for t in r2.json()["response"]["tracks"]]
    return {"art_url": art_url, "tracks": tracks}


def get_song_art(headers: dict, song_id: int) -> str:
    try:
        r = requests.get(f"{GENIUS_API}/songs/{song_id}", headers=headers, timeout=REQUEST_TIMEOUT)
        r.raise_for_status()
        song = r.json()["response"]["song"]
        return song.get("song_art_image_url") or song.get("header_image_thumbnail_url", "")
    except Exception:
        return ""


def fetch_lyrics(artist_name: str, title: str) -> list[str] | None:
    r = requests.get(f"{LRCLIB_API}/search",
                     params={"artist_name": artist_name, "track_name": title},
                     timeout=REQUEST_TIMEOUT)
    r.raise_for_status()
    results = r.json()
    if not results:
        return None
    plain = results[0].get("plainLyrics")
    return clean_lyrics(plain) if plain else None


_genius_client: lg.Genius | None = None


def _get_genius_client(token: str) -> lg.Genius:
    global _genius_client
    if _genius_client is None:
        _genius_client = lg.Genius(token, verbose=False, remove_section_headers=True)
    return _genius_client


def fetch_lyrics_from_genius(token: str, artist_name: str, title: str) -> list[str] | None:
    try:
        genius = _get_genius_client(token)
        song = genius.search_song(title, artist_name)
        if not song or not song.lyrics:
            return None
        # Strip the "NNNEmbed" footer that lyricsgenius appends
        raw = re.sub(r'\d*Embed.*$', '', song.lyrics, flags=re.DOTALL).strip()
        return clean_lyrics(raw) or None
    except Exception:
        return None


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--slug", required=True, help="Artist slug, e.g. taylor-swift")
    parser.add_argument("--incremental", action="store_true",
                        help="Keep existing lyrics; only fetch new songs + refresh metadata")
    args = parser.parse_args()

    slug = args.slug
    if slug not in ARTISTS:
        raise SystemExit(f"Unknown slug '{slug}'. Available: {', '.join(ARTISTS)}")

    token = os.environ.get("GENIUS_ACCESS_TOKEN")
    if not token:
        raise SystemExit("GENIUS_ACCESS_TOKEN not set in .env")

    artist_data = ARTISTS[slug]
    artist_name = artist_data["name"]
    headers = {"Authorization": f"Bearer {token}"}

    output_dir = Path(__file__).parent.parent / "public" / "data" / slug
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / "songs.json"

    # Load existing songs when running incrementally (keyed by Genius song ID)
    existing_by_id: dict[str, dict] = {}
    if args.incremental and output_path.exists():
        with open(output_path, encoding="utf-8") as f:
            for s in json.load(f):
                existing_by_id[str(s["id"])] = s
        print(f"Incremental mode — {len(existing_by_id)} songs cached, skipping lrclib for those\n")

    songs_output = []
    seen_titles: set[str] = set()

    # ── Album-based songs ───────────────────────────────────────────────────
    for album_meta in artist_data["albums"]:
        is_demo = album_meta.get("is_demo", False)
        display_album = DEMO_ALBUM_NAME if is_demo else album_meta["name"]

        print(f"\nFetching: {album_meta['name']} ({album_meta['year']}){' [demos]' if is_demo else ''}")
        try:
            info = get_album_info(headers, album_meta["genius_id"])
        except Exception as e:
            print(f"  WARNING: {e}")
            continue

        art = album_meta.get("art_override") or info["art_url"]
        print(f"  {len(info['tracks'])} tracks | art: {'yes' if art else 'no'}")

        for track in info["tracks"]:
            title = track["title"]
            title_lower = title.lower()
            # Skip commentary/studio session versions (not unique songs)
            if any(pattern in title_lower for pattern in SKIP_PATTERNS):
                print(f"  SKIP (commentary): {title}")
                continue
            canonical = title_lower.strip()
            if canonical in seen_titles:
                print(f"  SKIP (duplicate): {title}")
                continue
            seen_titles.add(canonical)

            song_id_str = str(track["id"])
            song_art = resolve_album_art(art, title)
            if song_id_str in existing_by_id:
                # Song already fetched — refresh metadata, keep lyrics
                kept = {**existing_by_id[song_id_str],
                        "albumArt": song_art, "album": display_album, "year": album_meta["year"]}
                songs_output.append(kept)
                print(f"  KEEP {title}")
                continue

            lines = fetch_lyrics(artist_name, title)
            if lines is None:
                lines = fetch_lyrics_from_genius(token, artist_name, title)
                if lines is not None:
                    print(f"  (genius fallback)")
            if lines is None:
                print(f"  SKIP (no lyrics): {title}")
                continue

            songs_output.append({
                "id":       track["id"],
                "title":    title,
                "album":    display_album,
                "year":     album_meta["year"],
                "albumArt": song_art,
                "lines":    lines,
            })
            print(f"  OK  {title} ({len(lines)} lines)")
            time.sleep(0.2)

    # ── Individual songs (collabs / features / standalone singles) ───────────
    if artist_data.get("individual_songs"):
        print(f"\n── Individual songs ──")
    for song_config in artist_data.get("individual_songs", []):
        title = song_config["title"]
        title_lower = title.lower()
        # Skip commentary/studio session versions (not unique songs)
        if any(pattern in title_lower for pattern in SKIP_PATTERNS):
            print(f"  SKIP (commentary): {title}")
            continue
        canonical = title_lower.strip()
        if canonical in seen_titles:
            print(f"  SKIP (duplicate): {title}")
            continue
        seen_titles.add(canonical)

        song_id_str = str(song_config["genius_id"])
        if song_id_str in existing_by_id:
            kept = {**existing_by_id[song_id_str],
                    "albumArt": song_config.get("art_override", existing_by_id[song_id_str].get("albumArt", "")),
                    "album": song_config.get("album", NON_ALBUM_COLLABS_NAME),
                    "year":  song_config.get("year", 0)}
            songs_output.append(kept)
            print(f"  KEEP {title}")
            continue

        search_artist = song_config.get("search_artist", artist_name)
        lines = fetch_lyrics(search_artist, title)
        if lines is None:
            lines = fetch_lyrics(artist_name, title)
        if lines is None:
            lines = fetch_lyrics_from_genius(token, artist_name, title)
            if lines is not None:
                print(f"  (genius fallback)")

        if lines is None:
            print(f"  SKIP (no lyrics): {title}")
            continue

        art = song_config.get("art_override") or get_song_art(headers, song_config["genius_id"])

        songs_output.append({
            "id":       song_config["genius_id"],
            "title":    title,
            "album":    song_config.get("album", NON_ALBUM_COLLABS_NAME),
            "year":     song_config.get("year", 0),
            "albumArt": art,
            "lines":    lines,
        })
        print(f"  OK  {title} ({len(lines)} lines)")
        time.sleep(0.3)

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(songs_output, f, ensure_ascii=False, indent=2)

    kept_count = sum(1 for s in songs_output if str(s["id"]) in existing_by_id)
    new_count  = len(songs_output) - kept_count
    total = len(songs_output)
    if args.incremental:
        print(f"\nDone. {total} songs ({kept_count} kept, {new_count} new) → {output_path}")
    else:
        print(f"\nDone. {total} songs → {output_path}")


if __name__ == "__main__":
    main()
