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
from dotenv import load_dotenv

load_dotenv()

# ---------------------------------------------------------------------------
# Artist catalogue — add new artists here.
# ---------------------------------------------------------------------------
ARTISTS = {
    "bleachers": {
        "name": "Bleachers",
        "albums": [
            {"name": "Strange Desire",                             "year": 2014, "genius_id": 108231},
            {"name": "Gone Now",                                   "year": 2017, "genius_id": 339923},
            {"name": "Take the Sadness Out of Saturday Night",     "year": 2021, "genius_id": 701041},
            {"name": "Bleachers",                                  "year": 2024, "genius_id": 1183217},
            {"name": "everyone for ten minutes",                   "year": 2026, "genius_id": 1581240},
        ],
        "individual_songs": [
            {"genius_id": 8659765, "title": "Merry Christmas, Please Don't Call", "album": "Non-album single", "year": 2023},
        ],
    },
    "taylor-swift": {
        "name": "Taylor Swift",
        "albums": [
            # Studio albums — in release order so dedup favours earlier versions
            {"name": "Taylor Swift",                               "year": 2006, "genius_id": 1034551},
            {"name": "The Taylor Swift Holiday Collection",        "year": 2007, "genius_id": 39094},
            {"name": "Fearless (Taylor's Version)",                "year": 2008, "genius_id": 734107},
            {"name": "Speak Now (Taylor's Version)",               "year": 2010, "genius_id": 1058580},
            {"name": "Red (Taylor's Version)",                     "year": 2012, "genius_id": 758022},
            {"name": "1989 (Taylor's Version)",                    "year": 2014, "genius_id": 1082316},
            {"name": "reputation",                                 "year": 2017, "genius_id": 1492663},
            {"name": "Lover",                                      "year": 2019, "genius_id": 832267},
            # Christmas Tree Farm single
            {"name": "The Taylor Swift Holiday Collection",        "year": 2019, "genius_id": 1271655},
            {"name": "folklore",                                   "year": 2020, "genius_id": 704621},
            {"name": "evermore",                                   "year": 2020, "genius_id": 726425},
            {"name": "Midnights",                                  "year": 2022, "genius_id": 1040211},
            {"name": "The Tortured Poets Department",              "year": 2024, "genius_id": 1260317},
            # The Life of a Showgirl + acoustic (one album entry, acoustic tracks
            # have different titles so they won't dedup with the originals)
            {"name": "The Life of a Showgirl",                    "year": 2025, "genius_id": 1517950},
            # Voice memos & demos — is_demo=True overrides album name in output
            # 1498620 = LoaS "So Punk on Internet" version: main songs dedup, only memos pass through
            {"name": "The Life of a Showgirl (Voice Memos)",      "year": 2025, "genius_id": 1498620, "is_demo": True},
            # cardigan voice memo single
            {"name": "cardigan voice memo",                       "year": 2020, "genius_id": 681918,  "is_demo": True},
            # willow webstore single (has lonely witch version + original songwriting demo)
            {"name": "willow demos",                              "year": 2020, "genius_id": 1513411, "is_demo": True},
        ],
        # Songs on other artists' albums where Taylor is a feature/collab
        "individual_songs": [
            {"genius_id": 187143,  "title": "Crazier",                    "album": "Collaborations & Features", "year": 2009},
            {"genius_id": 187250,  "title": "I'd Lie",                    "album": "Collaborations & Features", "year": 2006},
            {"genius_id": 187203,  "title": "I Heart ?",                  "album": "Collaborations & Features", "year": 2009},
            {"genius_id": 4968964, "title": "Beautiful Ghosts",           "album": "Collaborations & Features", "year": 2019},
            {"genius_id": 642957,  "title": "Two Is Better Than One",     "album": "Collaborations & Features", "year": 2009, "search_artist": "Boys Like Girls"},
            {"genius_id": 182948,  "title": "Half of My Heart",           "album": "Collaborations & Features", "year": 2010, "search_artist": "John Mayer"},
            {"genius_id": 70979,   "title": "Both of Us",                 "album": "Collaborations & Features", "year": 2012, "search_artist": "B.o.B"},
            {"genius_id": 154241,  "title": "Highway Don't Care",         "album": "Collaborations & Features", "year": 2013, "search_artist": "Tim McGraw"},
            {"genius_id": 3646550, "title": "Babe",                       "album": "Collaborations & Features", "year": 2018, "search_artist": "Sugarland"},
            {"genius_id": 2927948, "title": "I Don't Wanna Live Forever", "album": "Collaborations & Features", "year": 2017, "search_artist": "ZAYN"},
            {"genius_id": 6959851, "title": "Renegade",                   "album": "Collaborations & Features", "year": 2021, "search_artist": "Big Red Machine"},
            {"genius_id": 6959849, "title": "Birch",                      "album": "Collaborations & Features", "year": 2021, "search_artist": "Big Red Machine"},
            {"genius_id": 8714086, "title": "The Alcott",                 "album": "Collaborations & Features", "year": 2023, "search_artist": "The National"},
            {"genius_id": 6453633, "title": "Gasoline (Remix)",           "album": "Collaborations & Features", "year": 2021, "search_artist": "HAIM"},
        ],
    },
    "sabrina-carpenter": {
        "name": "Sabrina Carpenter",
        "albums": [
            {"name": "Eyes Wide Open",                              "year": 2015, "genius_id": 121108},
            {"name": "EVOLution",                                  "year": 2016, "genius_id": 168270},
            {"name": "Singular: Act I",                             "year": 2018, "genius_id": 923516},
            {"name": "Singular: Act II",                            "year": 2019, "genius_id": 927206},
            {"name": "emails i can't send",                        "year": 2022, "genius_id": 1008706},
            {"name": "Short n' Sweet",                             "year": 2024, "genius_id": 1330959},
        ],
    },
    "lana-del-rey": {
        "name": "Lana Del Rey",
        "albums": [
            {"name": "Born To Die",                                "year": 2012, "genius_id": 1298077},
            {"name": "Ultraviolence",                              "year": 2014, "genius_id": 1298656},
            {"name": "Honeymoon",                                  "year": 2015, "genius_id": 126114},
            {"name": "Lust for Life",                              "year": 2017, "genius_id": 331260},
            {"name": "Norman Fucking Rockwell!",                   "year": 2019, "genius_id": 459810},
            {"name": "Chemtrails over the Country Club",           "year": 2021, "genius_id": 621392},
            {"name": "Blue Banisters",                             "year": 2021, "genius_id": 749828},
            {"name": "Did You Know That There's a Tunnel Under Ocean Blvd", "year": 2023, "genius_id": 906956},
            {"name": "Charm",                                      "year": 2024, "genius_id": 1138487},
        ],
    },
    "olivia-rodrigo": {
        "name": "Olivia Rodrigo",
        "albums": [
            {"name": "SOUR",                                       "year": 2021, "genius_id": 715843},
            {"name": "GUTS",                                       "year": 2023, "genius_id": 1158939},
        ],
    },
    "ed-sheeran": {
        "name": "Ed Sheeran",
        "albums": [
            {"name": "+",                                          "year": 2011, "genius_id": 970831},
            {"name": "×",                                          "year": 2014, "genius_id": 954671},
            {"name": "÷",                                          "year": 2017, "genius_id": 1409684},
            {"name": "No.6 Collaborations Project",               "year": 2019, "genius_id": 531308},
            {"name": "=",                                          "year": 2021, "genius_id": 859330},
            {"name": "-",                                          "year": 2023, "genius_id": 1015321},
        ],
    },
    "gracie-abrams": {
        "name": "Gracie Abrams",
        "albums": [
            {"name": "Minor",                                       "year": 2020, "genius_id": 637845},
            {"name": "This Is What It Feels Like",                  "year": 2021, "genius_id": 820478},
            {"name": "Good Riddance",                              "year": 2023, "genius_id": 1028415},
            {"name": "The Secret of Us",                           "year": 2024, "genius_id": 1269000},
        ],
        "individual_songs": [
            {"genius_id": 4966804, "title": "Mean It", "album": "Non-album single", "year": 2019},
            {"genius_id": 5035258, "title": "Stay", "album": "Lonely Songs", "year": 2019},
            {"genius_id": 5437170, "title": "I Miss You, I'm Sorry", "album": "Non-album single", "year": 2020},
            {"genius_id": 5548061, "title": "Long Sleeves", "album": "Non-album single", "year": 2020},
            {"genius_id": 6257537, "title": "Brush Fire", "album": "Non-album single", "year": 2020},
            {"genius_id": 6780913, "title": "Mess It Up", "album": "Non-album single", "year": 2021},
            {"genius_id": 8444672, "title": "Where Do We Go Now?", "album": "Non-album single", "year": 2023},
            {"genius_id": 8250951, "title": "Difficult", "album": "Non-album single", "year": 2023},
            {"genius_id": 9647185, "title": "Risk", "album": "Non-album single", "year": 2024},
            {"genius_id": 11494841, "title": "Call Me When You Break Up", "album": "Non-album single", "year": 2025},
        ],
    },
    "the-weeknd": {
        "name": "The Weeknd",
        "albums": [
            {"name": "Kiss Land",                                  "year": 2013, "genius_id": 501331},
            {"name": "Beauty Behind the Madness",                  "year": 2015, "genius_id": 828707},
            {"name": "Starboy",                                    "year": 2016, "genius_id": 1011213},
            {"name": "After Hours",                                "year": 2020, "genius_id": 828696},
            {"name": "Dawn FM",                                    "year": 2022, "genius_id": 947480},
            {"name": "Hurry Up Tomorrow (00XO Edition)",         "year": 2025, "genius_id": 1322479},
        ],
    },
}

GENIUS_API = "https://api.genius.com"
LRCLIB_API = "https://lrclib.net/api"
SECTION_RE = re.compile(r'^\[.*\]$')
DEMO_ALBUM_NAME = "Voice Memos & Demos"


def clean_lyrics(raw: str) -> list[str]:
    lines = []
    for line in raw.split("\n"):
        line = line.strip()
        if not line or SECTION_RE.match(line):
            continue
        lines.append(line)
    return lines


def get_album_info(headers: dict, album_id: int) -> dict:
    r = requests.get(f"{GENIUS_API}/albums/{album_id}", headers=headers)
    r.raise_for_status()
    album = r.json()["response"]["album"]
    art_url = album.get("cover_art_url", "")

    r2 = requests.get(f"{GENIUS_API}/albums/{album_id}/tracks", headers=headers)
    r2.raise_for_status()
    tracks = [{"id": t["song"]["id"], "title": t["song"]["title"]}
              for t in r2.json()["response"]["tracks"]]
    return {"art_url": art_url, "tracks": tracks}


def get_song_art(headers: dict, song_id: int) -> str:
    try:
        r = requests.get(f"{GENIUS_API}/songs/{song_id}", headers=headers)
        r.raise_for_status()
        song = r.json()["response"]["song"]
        return song.get("song_art_image_url") or song.get("header_image_thumbnail_url", "")
    except Exception:
        return ""


def fetch_lyrics(artist_name: str, title: str) -> list[str] | None:
    r = requests.get(f"{LRCLIB_API}/search",
                     params={"artist_name": artist_name, "track_name": title})
    r.raise_for_status()
    results = r.json()
    if not results:
        return None
    plain = results[0].get("plainLyrics")
    return clean_lyrics(plain) if plain else None


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--slug", required=True, help="Artist slug, e.g. taylor-swift")
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
            canonical = title.lower().strip()
            if canonical in seen_titles:
                print(f"  SKIP (duplicate): {title}")
                continue
            seen_titles.add(canonical)

            lines = fetch_lyrics(artist_name, title)
            if lines is None:
                print(f"  SKIP (no lyrics): {title}")
                continue

            songs_output.append({
                "id":       track["id"],
                "title":    title,
                "album":    display_album,
                "year":     album_meta["year"],
                "albumArt": art,
                "lines":    lines,
            })
            print(f"  OK  {title} ({len(lines)} lines)")
            time.sleep(0.2)

    # ── Individual songs (collabs / features / standalone singles) ───────────
    if artist_data.get("individual_songs"):
        print(f"\n── Individual songs ──")
    for song_config in artist_data.get("individual_songs", []):
        title = song_config["title"]
        canonical = title.lower().strip()
        if canonical in seen_titles:
            print(f"  SKIP (duplicate): {title}")
            continue
        seen_titles.add(canonical)

        search_artist = song_config.get("search_artist", artist_name)
        lines = fetch_lyrics(search_artist, title)
        if lines is None:
            lines = fetch_lyrics(artist_name, title)

        if lines is None:
            print(f"  SKIP (no lyrics): {title}")
            continue

        art = get_song_art(headers, song_config["genius_id"])

        songs_output.append({
            "id":       song_config["genius_id"],
            "title":    title,
            "album":    song_config.get("album", "Collaborations & Features"),
            "year":     song_config.get("year", 0),
            "albumArt": art,
            "lines":    lines,
        })
        print(f"  OK  {title} ({len(lines)} lines)")
        time.sleep(0.3)

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(songs_output, f, ensure_ascii=False, indent=2)

    total = len(songs_output)
    print(f"\nDone. {total} songs → {output_path}")


if __name__ == "__main__":
    main()
