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
            # Art URLs from iTunes API (better quality than Genius)
            {"name": "Taylor Swift",                               "year": 2006, "genius_id": 1034551, "art_override": "https://is1-ssl.mzstatic.com/image/thumb/Music221/v4/be/e1/48/bee148d6-d16c-d8f7-0173-d6cf6d684aa1/08PNDIM00678.rgb.jpg/1000x1000bb.jpg"},
            {"name": "The Taylor Swift Holiday Collection",        "year": 2007, "genius_id": 39094, "art_override": "https://is1-ssl.mzstatic.com/image/thumb/Music126/v4/c6/01/8b/c6018b3e-ae83-e5ed-9003-5ddb70f4d237/18OPBMR00132.rgb.jpg/1000x1000bb.jpg"},
            {"name": "Fearless (Taylor's Version)",                "year": 2008, "genius_id": 734107, "art_override": "https://is1-ssl.mzstatic.com/image/thumb/Music125/v4/c3/d0/1c/c3d01c88-73e7-187e-fd62-e1744de979a6/21UMGIM09915.rgb.jpg/1000x1000bb.jpg"},
            {"name": "Speak Now (Taylor's Version)",               "year": 2010, "genius_id": 1058580, "art_override": "https://is1-ssl.mzstatic.com/image/thumb/Music126/v4/9f/3c/0a/9f3c0a60-f9e0-a34e-60e5-0be1f182896b/23UMGIM63932.rgb.jpg/1000x1000bb.jpg"},
            {"name": "Red (Taylor's Version)",                     "year": 2012, "genius_id": 758022, "art_override": "https://is1-ssl.mzstatic.com/image/thumb/Music115/v4/c6/27/9c/c6279c07-9329-827d-31c4-f5d4c7d99ff4/21UM1IM25046.rgb.jpg/1000x1000bb.jpg"},
            {"name": "1989 (Taylor's Version)",                    "year": 2014, "genius_id": 1082316, "art_override": "https://is1-ssl.mzstatic.com/image/thumb/Music116/v4/8e/35/6c/8e356cc2-0be4-b83b-d29e-b578623df2ac/23UM1IM34052.rgb.jpg/1000x1000bb.jpg"},
            {"name": "reputation",                                 "year": 2017, "genius_id": 1492663, "art_override": "https://is1-ssl.mzstatic.com/image/thumb/Music221/v4/eb/e6/06/ebe606da-e00f-82d3-47f3-b79904eed541/17UM1IM24651.rgb.jpg/1000x1000bb.jpg"},
            {"name": "Lover",                                      "year": 2019, "genius_id": 832267, "art_override": "https://is1-ssl.mzstatic.com/image/thumb/Music125/v4/49/3d/ab/493dab54-f920-9043-6181-80993b8116c9/19UMGIM53909.rgb.jpg/1000x1000bb.jpg"},
            # Christmas Tree Farm single
            {"name": "The Taylor Swift Holiday Collection",        "year": 2019, "genius_id": 1271655},
            {"name": "folklore",                                   "year": 2020, "genius_id": 704621, "art_override": "https://is1-ssl.mzstatic.com/image/thumb/Music125/v4/7c/04/ba/7c04ba17-2ff8-21b3-0ac0-7d141f86e924/20UMGIM64216.rgb.jpg/1000x1000bb.jpg"},
            {"name": "evermore",                                   "year": 2020, "genius_id": 726425, "art_override": "https://is1-ssl.mzstatic.com/image/thumb/Music115/v4/18/93/99/189399a7-95e1-324b-e40a-bd9e3ea22a95/20UM1IM14847.rgb.jpg/1000x1000bb.jpg"},
            {"name": "Midnights",                                  "year": 2022, "genius_id": 1040211, "art_override": "https://is1-ssl.mzstatic.com/image/thumb/Music126/v4/fb/b7/5d/fbb75d98-3b52-2fa5-ca82-658194f3c498/23UMGIM58157.rgb.jpg/1000x1000bb.jpg"},
            {"name": "The Tortured Poets Department",              "year": 2024, "genius_id": 1260317, "art_override": "https://is1-ssl.mzstatic.com/image/thumb/Music211/v4/a3/8a/8d/a38a8de5-ae11-154c-dca5-221e6549caee/24UMGIM44778.rgb.jpg/1000x1000bb.jpg"},
            # The Life of a Showgirl + acoustic (one album entry, acoustic tracks
            # have different titles so they won't dedup with the originals)
            {"name": "The Life of a Showgirl",                    "year": 2025, "genius_id": 1517950, "art_override": "https://is1-ssl.mzstatic.com/image/thumb/Music211/v4/30/0c/5a/300c5a57-d3be-a170-f880-f63380ca6312/25UM1IM19577.rgb.jpg/1000x1000bb.jpg"},
            # Voice memos & demos — is_demo=True overrides album name in output
            # 1498620 = LoaS "So Punk on Internet" version: main songs dedup, only memos pass through
            {"name": "The Life of a Showgirl (Voice Memos)",      "year": 2025, "genius_id": 1498620, "is_demo": True},
            # cardigan voice memo single
            {"name": "cardigan voice memo",                       "year": 2020, "genius_id": 681918,  "is_demo": True},
            # willow webstore single (has lonely witch version + original songwriting demo)
            {"name": "willow demos",                              "year": 2020, "genius_id": 1513411, "is_demo": True},
        ],
        # Songs on other artists' albums where Taylor is a feature/collab, plus standalone singles
        "individual_songs": [
            # Collaborations & features
            {"genius_id": 187143,  "title": "Crazier",                    "album": "Collaborations & Features", "year": 2009},
            {"genius_id": 187250,  "title": "I'd Lie",                    "album": "Collaborations & Features", "year": 2006},
            {"genius_id": 187203,  "title": "I Heart ?",                  "album": "Collaborations & Features", "year": 2009},
            {"genius_id": 4968964, "title": "Beautiful Ghosts",           "album": "Collaborations & Features", "year": 2019},
            {"genius_id": 1633487944, "title": "Carolina",                "album": "Where the Crawdads Sing - OST", "year": 2022, "art_override": "https://is1-ssl.mzstatic.com/image/thumb/Music122/v4/51/5f/41/515f417f-19d6-ea22-e1fb-acebc2ba4f23/22UMGIM67563.rgb.jpg/600x600bb.jpg"},
            {"genius_id": 642957,  "title": "Two Is Better Than One",     "album": "Collaborations & Features", "year": 2009, "search_artist": "Boys Like Girls"},
            {"genius_id": 182948,  "title": "Half of My Heart",           "album": "Collaborations & Features", "year": 2010, "search_artist": "John Mayer"},
            {"genius_id": 70979,   "title": "Both of Us",                 "album": "Collaborations & Features", "year": 2012, "search_artist": "B.o.B"},
            {"genius_id": 154241,  "title": "Highway Don't Care",         "album": "Collaborations & Features", "year": 2013, "search_artist": "Tim McGraw"},
            {"genius_id": 2927948, "title": "I Don't Wanna Live Forever", "album": "Collaborations & Features", "year": 2017, "search_artist": "ZAYN"},
            {"genius_id": 6959851, "title": "Renegade",                   "album": "Collaborations & Features", "year": 2021, "search_artist": "Big Red Machine"},
            {"genius_id": 6959849, "title": "Birch",                      "album": "Collaborations & Features", "year": 2021, "search_artist": "Big Red Machine"},
            {"genius_id": 8714086, "title": "The Alcott",                 "album": "Collaborations & Features", "year": 2023, "search_artist": "The National"},
            {"genius_id": 6453633, "title": "Gasoline (Remix)",           "album": "Collaborations & Features", "year": 2021, "search_artist": "HAIM"},
            # Standalone singles & vault tracks
            {"genius_id": 5651833, "title": "All of the Girls You Loved Before", "album": "Lover", "year": 2019},
            {"genius_id": 9157489, "title": "You're Losing Me (From The Vault)",  "album": "Midnights", "year": 2022},
            {"genius_id": 8924398, "title": "Eyes Open (Taylor's Version)",       "album": "Red (Taylor's Version)", "year": 2012},
            {"genius_id": 8924411, "title": "Safe & Sound (Taylor's Version)",    "album": "Red (Taylor's Version)", "year": 2012},
            {"genius_id": 6688373, "title": "If This Was a Movie (Taylor's Version)", "album": "Fearless (Taylor's Version)", "year": 2023},
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
            {"name": "Man's Best Friend (Bonus Track Version)",     "year": 2025, "genius_id": 1456877},
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
            # Art from iTunes API (better quality than Genius)
            {"name": "+",                                          "year": 2011, "genius_id": 970831, "art_override": "https://is1-ssl.mzstatic.com/image/thumb/Features124/v4/79/76/83/797683fd-dc59-e8a3-68be-fa4799485066/contsched.ptkgkexz.jpg/1000x1000bf-60.jpg"},
            {"name": "×",                                          "year": 2014, "genius_id": 954671, "art_override": "https://is1-ssl.mzstatic.com/image/thumb/Features125/v4/a7/7b/92/a77b92fc-d331-dd1b-8772-80597dc51fd0/dj.xllwtvne.jpg/1000x1000bb.jpg"},
            {"name": "÷",                                          "year": 2017, "genius_id": 1409684, "art_override": "https://is1-ssl.mzstatic.com/image/thumb/Music115/v4/15/e6/e8/15e6e8a4-4190-6a8b-86c3-ab4a51b88288/190295851286.jpg/1000x1000bb.jpg"},
            {"name": "No.6 Collaborations Project",               "year": 2019, "genius_id": 531308, "art_override": "https://is1-ssl.mzstatic.com/image/thumb/Music115/v4/e8/09/63/e809636b-2ea8-066e-2749-c0b94ab77052/190295384227.jpg/1000x1000bb.jpg"},
            {"name": "=",                                          "year": 2021, "genius_id": 859330, "art_override": "https://is1-ssl.mzstatic.com/image/thumb/Music122/v4/53/4a/01/534a01d1-d7c6-db04-7e00-b78cd4e50bfc/5054197180880.jpg/1000x1000bb.jpg"},
            {"name": "-",                                          "year": 2023, "genius_id": 1015321, "art_override": "https://is1-ssl.mzstatic.com/image/thumb/Music126/v4/c2/4c/36/c24c3631-08b8-b576-345a-259b395f8dbd/5054197591464.jpg/1000x1000bb.jpg"},
            {"name": "Autumn Variations",                            "year": 2023, "genius_id": 1015304, "art_override": "https://is1-ssl.mzstatic.com/image/thumb/Music116/v4/a5/48/07/a5480772-8c87-b4f7-7c09-c0c8ca32a90a/5054197787171.jpg/1000x1000bb.jpg"},
            {"name": "Play",                                         "year": 2025, "genius_id": 1391245, "art_override": "https://is1-ssl.mzstatic.com/image/thumb/Music211/v4/e5/40/89/e54089a9-5bc7-71c0-d7aa-93abadde2eb1/5021732960962.jpg/1000x1000bb.jpg"},
        ],
    },
    "harry-styles": {
        "name": "Harry Styles",
        "albums": [
            # Art from iTunes API
            {"name": "Harry Styles",                               "year": 2017, "genius_id": 339829,  "art_override": "https://is1-ssl.mzstatic.com/image/thumb/Music124/v4/3d/5e/aa/3d5eaaa3-9a86-c264-5cd5-7fac83f99a59/886446451978.jpg/1000x1000bb.jpg"},
            {"name": "Fine Line",                                  "year": 2019, "genius_id": 568792,  "art_override": "https://is1-ssl.mzstatic.com/image/thumb/Music115/v4/2b/c4/c9/2bc4c9d4-3bc6-ab13-3f71-df0b89b173de/886448022213.jpg/1000x1000bb.jpg"},
            {"name": "Harry's House",                              "year": 2022, "genius_id": 886451,  "art_override": "https://is1-ssl.mzstatic.com/image/thumb/Music126/v4/2a/19/fb/2a19fb85-2f70-9e44-f2a9-82abe679b88e/886449990061.jpg/1000x1000bb.jpg"},
            {"name": "Kiss All The Time. Disco, Occasionally.",    "year": 2025, "genius_id": 1552425, "art_override": "https://is1-ssl.mzstatic.com/image/thumb/Music221/v4/07/41/6a/07416a78-38b9-2d47-7ce8-8a52a44c510f/196874010112.jpg/1000x1000bb.jpg"},
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
            {"genius_id": 10541726, "title": "That's So True", "album": "The Secret of Us (Digital Deluxe)", "year": 2024},
            {"genius_id": 11570039, "title": "Death Wish", "album": "Non-album single", "year": 2025},
        ],
    },
    "the-weeknd": {
        "name": "The Weeknd",
        "albums": [
            {"name": "Kiss Land",                                  "year": 2013, "genius_id": 501331},
            {"name": "Beauty Behind the Madness",                  "year": 2015, "genius_id": 828707},
            {"name": "Starboy",                                    "year": 2016, "genius_id": 1011213},
            {"name": "My Dear Melancholy,",                        "year": 2018, "genius_id": 1427990, "art_override": "https://is1-ssl.mzstatic.com/image/thumb/Music125/v4/db/22/4e/db224ee0-b058-5d06-9a8c-fa10662bd58e/18UMGIM17205.rgb.jpg/1000x1000bb.jpg"},
            {"name": "After Hours",                                "year": 2020, "genius_id": 828696},
            {"name": "Dawn FM",                                    "year": 2022, "genius_id": 947480},
            {"name": "Hurry Up Tomorrow (00XO Edition)",         "year": 2025, "genius_id": 1322479},
        ],
        "individual_songs": [
            {"genius_id": 3614919, "title": "Call Out My Name", "album": "My Dear Melancholy,", "year": 2018},
            {"genius_id": 3614925, "title": "Try Me", "album": "My Dear Melancholy,", "year": 2018},
            {"genius_id": 3614873, "title": "Wasted Times", "album": "My Dear Melancholy,", "year": 2018},
            {"genius_id": 3614926, "title": "I Was Never There", "album": "My Dear Melancholy,", "year": 2018},
            {"genius_id": 3614927, "title": "Hurt You", "album": "My Dear Melancholy,", "year": 2018},
            {"genius_id": 3614928, "title": "Privilege", "album": "My Dear Melancholy,", "year": 2018},
        ],
    },
}

GENIUS_API = "https://api.genius.com"
LRCLIB_API = "https://lrclib.net/api"
SECTION_RE = re.compile(r'^\[.*\]$')
DEMO_ALBUM_NAME = "Voice Memos & Demos"
LONG_POND_ART_URL = "https://is1-ssl.mzstatic.com/image/thumb/Music114/v4/0f/a0/14/0fa0144d-6cd5-792a-1589-3e1f0c25db49/20UM1IM08851.rgb.jpg/600x600bb.jpg"
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
                    "album": song_config.get("album", "Collaborations & Features"),
                    "year":  song_config.get("year", 0)}
            songs_output.append(kept)
            print(f"  KEEP {title}")
            continue

        search_artist = song_config.get("search_artist", artist_name)
        lines = fetch_lyrics(search_artist, title)
        if lines is None:
            lines = fetch_lyrics(artist_name, title)

        if lines is None:
            print(f"  SKIP (no lyrics): {title}")
            continue

        art = song_config.get("art_override") or get_song_art(headers, song_config["genius_id"])

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

    kept_count = sum(1 for s in songs_output if str(s["id"]) in existing_by_id)
    new_count  = len(songs_output) - kept_count
    total = len(songs_output)
    if args.incremental:
        print(f"\nDone. {total} songs ({kept_count} kept, {new_count} new) → {output_path}")
    else:
        print(f"\nDone. {total} songs → {output_path}")


if __name__ == "__main__":
    main()
