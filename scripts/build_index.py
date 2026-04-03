"""
build_index.py
--------------
Builds an inverted index for a given artist slug.

Usage:
  python build_index.py --slug bleachers
  python build_index.py --slug taylor-swift
"""

import json, re, argparse
from pathlib import Path

BASE = Path(__file__).parent.parent / "public" / "data"


def tokenize(text: str) -> list[str]:
    text = text.lower()
    text = re.sub(r"'", "", text)
    text = re.sub(r"[^a-z0-9\s]", " ", text)
    return text.split()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--slug", required=True)
    args = parser.parse_args()

    songs_path = BASE / args.slug / "songs.json"
    index_path = BASE / args.slug / "index.json"

    with open(songs_path, encoding="utf-8") as f:
        songs = json.load(f)

    index: dict[str, dict[str, list[list[int]]]] = {}

    for song in songs:
        sid = str(song["id"])
        for line_idx, line in enumerate(song["lines"]):
            for word_idx, token in enumerate(tokenize(line)):
                if token not in index:
                    index[token] = {}
                if sid not in index[token]:
                    index[token][sid] = []
                index[token][sid].append([line_idx, word_idx])

    with open(index_path, "w", encoding="utf-8") as f:
        json.dump(index, f, ensure_ascii=False, separators=(",", ":"))

    total = sum(sum(len(v) for v in sm.values()) for sm in index.values())
    print(f"{args.slug}: {len(songs)} songs, {len(index)} tokens, {total} occurrences → {index_path}")


if __name__ == "__main__":
    main()
