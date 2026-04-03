# 02 — Data Pipeline

## What was built
Two Python scripts that run once on your machine to produce the data the app needs:

1. `scripts/fetch_lyrics.py` — calls the Genius API, downloads every Bleachers song with its lyrics, and writes `public/data/songs.json`
2. `scripts/build_index.py` — reads `songs.json`, tokenizes every line of every song, and writes `public/data/index.json`

The React app never calls the Genius API. It only reads the pre-built JSON files.

---

## Why pre-build instead of fetching at runtime?

Three reasons:

**Speed.** Loading two local JSON files takes milliseconds. Fetching 80+ songs from the Genius API in the browser would take 30–60 seconds and require handling rate limits, retries, and loading states. Pre-building moves that cost to your machine, once.

**No API key in the browser.** If you called Genius from the browser, your secret token would be visible in the JavaScript source — anyone could steal it and use your quota. Keeping the script on your machine keeps the key private.

**Stability.** The Genius API can change, go down, or rate-limit you. Once the JSON is built, the app works offline and forever, regardless of API status.

---

## How the Genius API works

Genius is a lyrics website. They have an API that lets you search for songs, albums, and artists, and retrieve lyrics. You need a free account and a "client access token" to use it.

We use a Python library called `lyricsgenius` which wraps the Genius API and makes it much easier to use — for example, `genius.search_album("Gone Now", "Bleachers")` fetches the entire album in one call.

### Getting your token
1. Go to https://genius.com/api-clients
2. Sign in (or create a free account)
3. Click "New API Client"
4. Fill in any name and URL (these don't matter for personal use)
5. Copy the "Client Access Token"
6. Put it in `scripts/.env`:
   ```
   GENIUS_ACCESS_TOKEN=paste_your_token_here
   ```

---

## What fetch_lyrics.py does, step by step

```
1. Load the token from .env
2. For each album in our hardcoded ALBUMS list:
   a. Ask Genius: "give me the album 'Strange Desire' by Bleachers"
   b. For each track on that album:
      - Skip if we've already seen a song with this title (deduplication)
      - Skip if Genius has no lyrics for it
      - Clean the lyrics: strip [Verse 1], [Chorus] etc., remove blank lines
      - Save: { id, title, album, year, lines: [...] }
   c. Wait 0.5 seconds before the next request (rate limit protection)
3. Write the full list to public/data/songs.json
```

### Why strip [Verse 1], [Chorus] etc.?
These section headers are added by Genius editors, not by the artist. Searching for a lyric phrase should find actual sung words, not formatting labels. Regex `^\[.*\]$` catches any line that is entirely a bracket-wrapped label.

### Why deduplicate by title?
Genius sometimes has the same song listed multiple times — the album version, a single version, a live version. By tracking seen titles (lowercased), we keep the first instance we encounter and skip duplicates, preventing the same song appearing multiple times in search results.

---

## What build_index.py does, step by step

```
1. Read songs.json
2. For each song → for each line → for each word:
   a. Normalize the word (tokenize): lowercase, remove apostrophes, strip punctuation
   b. Record: index[word][songId] = [[lineIndex, wordIndex], ...]
3. Write compact JSON to public/data/index.json
```

### What is a token?
"Tokenizing" means splitting text into the smallest meaningful units (tokens) and normalizing them so comparisons work. For us, a token is just a single word, normalized.

Example:
```
Input line:  "I didn't know I was broken till I wanted to change"
Tokens:      ["i", "didnt", "know", "i", "was", "broken", "till", "i", "wanted", "to", "change"]
```

`"didn't"` → `"didnt"` because we remove apostrophes. This way, a user searching for `didnt` or `didn't` both match — because the index only knows about `didnt`.

### The index structure
```json
{
  "better": {
    "1234567": [[1, 3], [1, 7], [5, 0]],
    "7654321": [[0, 2]]
  }
}
```

Reading this: the word `"better"` appears in song `1234567` at line 1 word 3, line 1 word 7, and line 5 word 0. It also appears in song `7654321` at line 0 word 2.

This is called an **inverted index** — instead of asking "what words are in this song?", you can ask "which songs contain this word?" in O(1) time (a single dictionary lookup).

### Why store word positions?
Word-level positions `[lineIndex, wordIndex]` are what make phrase search work. To find the phrase "I wanna get better", the search algorithm:
1. Finds all positions of "i"
2. Finds all positions of "wanna"
3. Checks if any "i" position is immediately followed by "wanna" at `[sameLine, wordIndex+1]`
4. Repeats for "get" and "better"

Without positions, you could only tell "this song contains all four words" — not whether they appear consecutively.

---

## Running the pipeline

```bash
cd scripts

# First time only: create a virtual environment and install dependencies
python3 -m venv .venv
source .venv/bin/activate   # on Windows: .venv\Scripts\activate
pip install -r requirements.txt

# Copy the env template and add your token
cp .env.example .env
# edit .env and paste your GENIUS_ACCESS_TOKEN

# Step 1: fetch lyrics (takes ~3–5 minutes, ~80 API calls)
python fetch_lyrics.py

# Step 2: build the index (takes ~1 second)
python build_index.py
```

After running, you'll see two new files:
- `public/data/songs.json` — ~200KB
- `public/data/index.json` — ~400–600KB

---

## If something breaks

- **`GENIUS_ACCESS_TOKEN not set`**: you haven't created `scripts/.env` or forgot to add the token
- **`WARNING: album not found`**: Genius doesn't have that album — try searching for it manually on genius.com to see the exact title they use, then update `ALBUMS` in `fetch_lyrics.py`
- **`lyricsgenius.exceptions.HTTPError: 429`**: rate limit hit — add a longer `time.sleep()` value
- **songs.json looks small (< 40 songs)**: some albums may have failed; check the script output for warnings
- **index.json missing**: `build_index.py` wasn't run, or `songs.json` doesn't exist yet
