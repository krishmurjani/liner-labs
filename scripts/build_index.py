"""
build_index.py
--------------
Reads public/data/songs.json and builds an inverted index written to
public/data/index.json.

Run after fetch_lyrics.py:
  cd scripts
  python build_index.py

The inverted index maps each word to the songs and positions where it appears,
enabling O(1) single-word lookup and fast phrase search in the browser.

Index schema:
  {
    "word": {
      "songId": [[lineIndex, wordIndex], ...]
    }
  }
"""

import json
import re
from pathlib import Path

SONGS_PATH = Path(__file__).parent.parent / "public" / "data" / "songs.json"
INDEX_PATH = Path(__file__).parent.parent / "public" / "data" / "index.json"


def tokenize(text: str) -> list[str]:
    """
    Normalize text into a list of tokens.

    Rules (must stay identical to src/lib/tokenize.ts in the React app):
      1. Lowercase
      2. Remove apostrophes entirely  →  "can't" becomes "cant"
      3. Replace non-alphanumeric with spaces  →  hyphens, commas, etc. become word breaks
      4. Split on whitespace, drop empty strings

    Why remove apostrophes instead of splitting on them?
      Splitting "can't" → ["can", "t"] makes "t" a useless token and breaks
      the connection between "cant" (what users type) and "can't" (in lyrics).
      Removing the apostrophe keeps the contraction as one recognisable word.
    """
    text = text.lower()
    text = re.sub(r"'", "", text)           # remove apostrophes
    text = re.sub(r"[^a-z0-9\s]", " ", text)  # other punct → space
    return text.split()


def main():
    with open(SONGS_PATH, encoding="utf-8") as f:
        songs = json.load(f)

    # index: token → { str(songId): [[lineIdx, wordIdx], ...] }
    index: dict[str, dict[str, list[list[int]]]] = {}

    for song in songs:
        sid = str(song["id"])
        for line_idx, line in enumerate(song["lines"]):
            tokens = tokenize(line)
            for word_idx, token in enumerate(tokens):
                if token not in index:
                    index[token] = {}
                if sid not in index[token]:
                    index[token][sid] = []
                index[token][sid].append([line_idx, word_idx])

    INDEX_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(INDEX_PATH, "w", encoding="utf-8") as f:
        # separators=(',', ':') produces compact JSON (no spaces) — smaller file
        json.dump(index, f, ensure_ascii=False, separators=(",", ":"))

    total_tokens = len(index)
    total_postings = sum(
        sum(len(positions) for positions in song_map.values())
        for song_map in index.values()
    )
    print(f"Index built:")
    print(f"  {len(songs)} songs")
    print(f"  {total_tokens} unique tokens")
    print(f"  {total_postings} total word occurrences")
    print(f"  Written to {INDEX_PATH}")


if __name__ == "__main__":
    main()
