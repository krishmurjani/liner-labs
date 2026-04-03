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
"""

import os, json, re, time, argparse
from pathlib import Path
import requests
from dotenv import load_dotenv

load_dotenv()

# ---------------------------------------------------------------------------
# Artist catalogue — add new artists here.
# genius_id: find by searching Genius API for a known song, then GET /songs/{id}
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
    },
    "taylor-swift": {
        "name": "Taylor Swift",
        "albums": [
            {"name": "Fearless (Taylor's Version)",                "year": 2008, "genius_id": 904481},
            {"name": "Speak Now (Taylor's Version)",               "year": 2010, "genius_id": 969246},
            {"name": "Red (Taylor's Version)",                     "year": 2012, "genius_id": 881930},
            {"name": "1989 (Taylor's Version)",                    "year": 2014, "genius_id": 927214},
            {"name": "reputation",                                 "year": 2017, "genius_id": 364560},
            {"name": "Lover",                                      "year": 2019, "genius_id": 594985},
            {"name": "folklore",                                   "year": 2020, "genius_id": 672785},
            {"name": "evermore",                                   "year": 2020, "genius_id": 724703},
            {"name": "Midnights",                                  "year": 2022, "genius_id": 863177},
            {"name": "The Tortured Poets Department",              "year": 2024, "genius_id": 1011960},
        ],
    },
    "sabrina-carpenter": {
        "name": "Sabrina Carpenter",
        "albums": [
            {"name": "emails i can't send",                        "year": 2022, "genius_id": 847685},
            {"name": "Short n' Sweet",                             "year": 2024, "genius_id": 1005864},
        ],
    },
    "lana-del-rey": {
        "name": "Lana Del Rey",
        "albums": [
            {"name": "Born To Die",                                "year": 2012, "genius_id": 8432},
            {"name": "Ultraviolence",                              "year": 2014, "genius_id": 53552},
            {"name": "Honeymoon",                                  "year": 2015, "genius_id": 96668},
            {"name": "Lust for Life",                              "year": 2017, "genius_id": 299988},
            {"name": "Norman Fucking Rockwell!",                   "year": 2019, "genius_id": 572468},
            {"name": "Chemtrails over the Country Club",           "year": 2021, "genius_id": 702662},
            {"name": "Blue Banisters",                             "year": 2021, "genius_id": 737264},
            {"name": "Did You Know That There's a Tunnel Under Ocean Blvd", "year": 2023, "genius_id": 893019},
            {"name": "Charm",                                      "year": 2024, "genius_id": 1001548},
        ],
    },
    "olivia-rodrigo": {
        "name": "Olivia Rodrigo",
        "albums": [
            {"name": "SOUR",                                       "year": 2021, "genius_id": 716892},
            {"name": "GUTS",                                       "year": 2023, "genius_id": 935308},
        ],
    },
    "ed-sheeran": {
        "name": "Ed Sheeran",
        "albums": [
            {"name": "+",                                          "year": 2011, "genius_id": 3964},
            {"name": "×",                                          "year": 2014, "genius_id": 46407},
            {"name": "÷",                                          "year": 2017, "genius_id": 291064},
            {"name": "No.6 Collaborations Project",               "year": 2019, "genius_id": 570897},
            {"name": "=",                                          "year": 2021, "genius_id": 737018},
            {"name": "-",                                          "year": 2023, "genius_id": 915510},
        ],
    },
    "gracie-abrams": {
        "name": "Gracie Abrams",
        "albums": [
            {"name": "Good Riddance",                              "year": 2023, "genius_id": 898518},
            {"name": "The Secret of Us",                           "year": 2024, "genius_id": 998682},
        ],
    },
    "the-weeknd": {
        "name": "The Weeknd",
        "albums": [
            {"name": "Kiss Land",                                  "year": 2013, "genius_id": 30877},
            {"name": "Beauty Behind the Madness",                  "year": 2015, "genius_id": 102154},
            {"name": "Starboy",                                    "year": 2016, "genius_id": 243449},
            {"name": "After Hours",                                "year": 2020, "genius_id": 663375},
            {"name": "Dawn FM",                                    "year": 2022, "genius_id": 800346},
            {"name": "Hurry Up Tomorrow",                          "year": 2025, "genius_id": 1070978},
        ],
    },
}

GENIUS_API = "https://api.genius.com"
LRCLIB_API = "https://lrclib.net/api"
SECTION_RE = re.compile(r'^\[.*\]$')


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

    for album_meta in artist_data["albums"]:
        print(f"\nFetching: {album_meta['name']} ({album_meta['year']})")
        try:
            info = get_album_info(headers, album_meta["genius_id"])
        except Exception as e:
            print(f"  WARNING: {e}")
            continue

        print(f"  {len(info['tracks'])} tracks | art: {'yes' if info['art_url'] else 'no'}")

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
                "album":    album_meta["name"],
                "year":     album_meta["year"],
                "albumArt": info["art_url"],
                "lines":    lines,
            })
            print(f"  OK  {title} ({len(lines)} lines)")
            time.sleep(0.2)

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(songs_output, f, ensure_ascii=False, indent=2)

    print(f"\nDone. {len(songs_output)} songs → {output_path}")


if __name__ == "__main__":
    main()
