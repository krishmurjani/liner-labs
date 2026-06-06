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


# ── Variant de-duplication ──────────────────────────────────────────────────
# A "variant" is a non-canonical recording of a song already in the catalogue
# (live, remix, acoustic, etc.). We hide variants when the studio original is
# present, but keep a variant when (a) it's the only version of that song, or
# (b) it has a guest artist who may add a verse (Genius featured_artists).

# Parenthetical/suffix descriptors that mark a non-canonical variant.
VARIANT_KEYWORDS = (
    "remix", "live", "acoustic", "instrumental", "demo", "voice memo",
    "a cappella", "acapella", "recorded at", "recorded live", "session",
    "spotify singles", "amazon music", "radio edit", "radio mix",
    "single version", "rework", "sped up", "slowed",
)
# Never strip these — they denote canonical or otherwise-distinct songs.
PROTECTED_KEYWORDS = ("taylor's version", "from the vault", "extended", "minute version")

# Trailing "(…)" (allowing one level of nesting, e.g. "(Live (BBC Recording))")
# or "- …" descriptor.
_VARIANT_SUFFIX_RE = re.compile(r'\s*(\((?:[^()]|\([^()]*\))*\)|-\s[^-]+)\s*$')


def _strip_variant_suffix(title: str) -> str:
    """Remove trailing '(…)' or '- …' descriptors that contain a variant keyword."""
    base = title
    while True:
        m = _VARIANT_SUFFIX_RE.search(base)
        if not m:
            break
        seg = m.group(0).lower()
        if any(k in seg for k in PROTECTED_KEYWORDS):
            break
        if any(k in seg for k in VARIANT_KEYWORDS):
            base = base[:m.start()].rstrip()
            continue
        break
    return base


def _norm(title: str) -> str:
    return title.lower().replace("’", "'").strip()


def _select_keepers(candidates: list[dict]) -> list[dict]:
    """Collapse variant recordings to their canonical song.

    Each candidate is a dict with at least: id, title, featured (list[str]),
    is_individual (bool). Returns the subset to actually publish.
    """
    groups: dict[str, list[dict]] = {}
    for c in candidates:
        base = _norm(_strip_variant_suffix(c["title"]))
        c["_is_variant"] = base != _norm(c["title"])
        groups.setdefault(base, []).append(c)

    keepers, seen_ids = [], set()
    for group in groups.values():
        individuals = [c for c in group if c["is_individual"]]
        album = [c for c in group if not c["is_individual"]]
        originals = [c for c in album if not c["_is_variant"]]

        chosen = list(individuals)  # curated collabs are always kept
        if originals:
            chosen.append(originals[0])
            # A variant survives only if it adds a guest the original doesn't
            # have (a new feature may add a verse). Live/alt cuts that merely
            # inherit the original's guest are dropped.
            orig_feat = {f.lower() for o in originals for f in o["featured"]}
            chosen += [c for c in album if c["_is_variant"]
                       and {f.lower() for f in c["featured"]} - orig_feat]
        elif not individuals:
            # No studio original and no curated single — keep one representative
            # (prefer a featured cut) so the song isn't lost entirely.
            feat = [c for c in album if c["featured"]]
            chosen += feat[:1] if feat else album[:1]
        # else: only variants remain but a curated single covers them → drop variants

        for c in chosen:
            if c["id"] not in seen_ids:
                seen_ids.add(c["id"])
                keepers.append(c)
    return keepers


def get_album_info(headers: dict, album_id: int) -> dict:
    r = requests.get(f"{GENIUS_API}/albums/{album_id}", headers=headers, timeout=REQUEST_TIMEOUT)
    r.raise_for_status()
    album = r.json()["response"]["album"]
    art_url = album.get("cover_art_url", "")

    r2 = requests.get(f"{GENIUS_API}/albums/{album_id}/tracks", headers=headers, timeout=REQUEST_TIMEOUT)
    r2.raise_for_status()
    tracks = [{"id": t["song"]["id"],
               "title": t["song"]["title"],
               "featured": [a["name"] for a in t["song"].get("featured_artists", [])]}
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
# Genius blocks the default lyricsgenius User-Agent (403); a browser UA works.
_BROWSER_UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
               "(KHTML, like Gecko) Chrome/124.0 Safari/537.36")


def _get_genius_client(token: str) -> lg.Genius:
    global _genius_client
    if _genius_client is None:
        _genius_client = lg.Genius(token, verbose=False, remove_section_headers=True,
                                   timeout=15, retries=2)
        _genius_client._session.headers["User-Agent"] = _BROWSER_UA
    return _genius_client


def _clean_genius_raw(raw: str) -> list[str] | None:
    """Strip Genius page chrome from a lyricsgenius result.

    The result is prefixed with a one-line header blob
    ("N Contributors … <Title> Lyrics[<about> Read More]") and suffixed with
    a "NNNEmbed" marker. Remove both, then the section headers.
    """
    if not raw:
        return None
    # Header: drop "N Contributors … Lyrics", then any "<about> … Read More".
    raw = re.sub(r'^\d+\s+Contributor.*?Lyrics', '', raw, count=1, flags=re.DOTALL).lstrip()
    raw = re.sub(r'^.{0,2000}?Read More', '', raw, count=1, flags=re.DOTALL).lstrip()
    # Footer: a view-count + "Embed" marker, e.g. "…6.8KEmbed" / "…27Embed" / "…Embed"
    raw = re.sub(r'\d+(?:\.\d+)?[KM]?Embed\s*$', '', raw)
    raw = re.sub(r'Embed\s*$', '', raw).strip()
    return clean_lyrics(raw) or None


def fetch_lyrics_by_genius_id(token: str, song_id: int) -> list[str] | None:
    """Scrape lyrics directly from a known Genius song page.

    Preferred over search_song() because brand-new releases are reachable via
    the album-tracks API before Genius's search index catches up.
    """
    try:
        genius = _get_genius_client(token)
        return _clean_genius_raw(genius.lyrics(song_id=song_id))
    except Exception as e:
        print(f"    genius fallback error ({song_id}): {e}")
        return None


def fetch_lyrics_from_genius(token: str, artist_name: str, title: str) -> list[str] | None:
    try:
        genius = _get_genius_client(token)
        song = genius.search_song(title, artist_name)
        return _clean_genius_raw(song.lyrics) if song else None
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

    # ── Pass 1: gather every candidate track (cheap album-tracks API only) ───
    candidates: list[dict] = []

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
            # Skip commentary/interview versions (not unique songs)
            if any(pattern in title.lower() for pattern in SKIP_PATTERNS):
                print(f"  SKIP (commentary): {title}")
                continue
            candidates.append({
                "id":            track["id"],
                "title":         title,
                "album":         display_album,
                "year":          album_meta["year"],
                "albumArt":      resolve_album_art(art, title),
                "featured":      track.get("featured", []),
                "is_individual": False,
            })

    for song_config in artist_data.get("individual_songs", []):
        title = song_config["title"]
        if any(pattern in title.lower() for pattern in SKIP_PATTERNS):
            print(f"  SKIP (commentary): {title}")
            continue
        candidates.append({
            "id":            song_config["genius_id"],
            "title":         title,
            "album":         song_config.get("album", NON_ALBUM_COLLABS_NAME),
            "year":          song_config.get("year", 0),
            "albumArt":      None,  # resolved lazily on keep (needs get_song_art)
            "featured":      [],
            "is_individual": True,
            "search_artist": song_config.get("search_artist", artist_name),
            "art_override":  song_config.get("art_override"),
        })

    # ── Pass 2: collapse variant recordings to their canonical song ──────────
    keepers = _select_keepers(candidates)
    dropped = len(candidates) - len(keepers)
    print(f"\n── Selected {len(keepers)} songs ({dropped} variant/duplicate dropped) ──")

    # ── Pass 3: fetch lyrics only for the songs we actually keep ─────────────
    songs_output = []
    for c in keepers:
        title = c["title"]
        song_id_str = str(c["id"])

        if song_id_str in existing_by_id:
            # Song already fetched — refresh metadata, keep lyrics
            if c["is_individual"]:
                album_art = c["art_override"] or existing_by_id[song_id_str].get("albumArt", "")
            else:
                album_art = c["albumArt"]
            songs_output.append({**existing_by_id[song_id_str],
                                  "albumArt": album_art, "album": c["album"], "year": c["year"]})
            print(f"  KEEP {title}")
            continue

        if c["is_individual"]:
            lines = fetch_lyrics(c["search_artist"], title) or fetch_lyrics(artist_name, title)
        else:
            lines = fetch_lyrics(artist_name, title)
        if lines is None:
            lines = fetch_lyrics_by_genius_id(token, c["id"])
            if lines is not None:
                print(f"  (genius fallback) {title}")
        if lines is None:
            print(f"  SKIP (no lyrics): {title}")
            continue

        if c["is_individual"]:
            album_art = c["art_override"] or get_song_art(headers, c["id"])
        else:
            album_art = c["albumArt"]

        songs_output.append({
            "id":       c["id"],
            "title":    title,
            "album":    c["album"],
            "year":     c["year"],
            "albumArt": album_art,
            "lines":    lines,
        })
        print(f"  OK  {title} ({len(lines)} lines)")
        time.sleep(0.2)

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
