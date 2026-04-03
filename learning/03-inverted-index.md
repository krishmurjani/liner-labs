# 03 — Inverted Index

## What was built
The core data structure that makes fast search possible: an **inverted index** stored in `public/data/index.json`, built by `scripts/build_index.py`.

---

## What is an inverted index?

Think of a book's index at the back — it maps words to page numbers. An inverted index is the same idea, but for search engines.

**Normal (forward) direction**: "Song → Words"
- "I Wanna Get Better" contains: ["i", "wanna", "get", "better", ...]

**Inverted direction**: "Word → Songs"
- "better" appears in: ["I Wanna Get Better" (line 1), "How Dare You Want More" (line 4), ...]

The "inverted" in the name just means we flipped the direction of the lookup.

---

## Why does inverting help?

Imagine you want to find all songs containing "better". Without an inverted index you'd have to:
1. Open "Wild Heart", read every word — no match
2. Open "Rollercoaster", read every word — no match
3. Open "I Wanna Get Better", read every word — match!
4. ...repeat for all 54 songs

That's a **linear scan** — O(n) where n is the total number of words across all lyrics. Fine for 54 songs, sluggish for thousands.

With an inverted index, step 1 is just:
```
index["better"]  →  instant hash lookup  →  { songId: positions }
```
One operation. O(1). Same speed whether you have 54 songs or 54,000.

---

## The exact structure in index.json

```json
{
  "better": {
    "390927": [[1, 3], [1, 7], [5, 0]],
    "6824164": [[0, 2]]
  },
  "wanna": {
    "390927": [[1, 1], [5, 1]]
  }
}
```

Reading the first entry: the word `"better"` appears in:
- Song `390927` at line 1 word 3, line 1 word 7, and line 5 word 0
- Song `6824164` at line 0 word 2

Both indices are **zero-based** (first line = line 0, first word = word 0).

---

## Why store word positions?

If we only stored which songs contain a word, phrase search would be impossible.

Knowing "I Wanna Get Better" contains both "wanna" and "get" tells us nothing about whether they appear next to each other. They might be in completely different parts of the song.

Storing `[lineIndex, wordIndex]` for every occurrence lets the search algorithm verify adjacency:
- "wanna" at position [1, 1]
- "get" at position [1, 2] ← same line, wordIndex = 1+1 ✓
- "better" at position [1, 3] ← same line, wordIndex = 2+1 ✓

That's how we confirm "wanna get better" is a real phrase and not just three words that happen to be in the same song.

---

## The tokenization step (why words look different in the index)

Before adding a word to the index, `build_index.py` normalizes it:

| Raw text in lyrics | Token in index |
|---|---|
| `"I"` | `"i"` |
| `"can't"` | `"cant"` |
| `"Better,"` | `"better"` |
| `"twenty-one"` | `"twenty"` and `"one"` (two tokens) |

Normalization means a user typing `cant` and `can't` both hit the same index entry. Without it, you'd need a separate entry for every punctuation variant of every word.

**Critical rule**: the tokenizer in `scripts/build_index.py` and the tokenizer in `src/lib/tokenize.ts` must be **byte-for-byte identical**. If a user types a query, it goes through the TypeScript tokenizer. If the index was built with different rules, the tokens won't match and search will silently return nothing.

---

## Size and performance

For 54 Bleachers songs:
- **1,446 unique tokens** — the vocabulary
- **15,176 total word occurrences** — positions stored across all songs
- **index.json file size**: ~200KB uncompressed

When the React app loads, this fits entirely in memory. A search is literally a JavaScript object property access — `index["better"]` — which takes microseconds. There's no network call, no database query, no loop over all songs.

---

## What's NOT in the index

- **Section headers** ([Verse 1], [Chorus]) — stripped during cleaning
- **Blank lines** — stripped during cleaning
- **Punctuation as tokens** — commas, periods, etc. become word boundaries
- **Stop words** — "the", "a", "in" ARE indexed (needed for phrase search like "in the end")

---

## Key files
- `scripts/build_index.py` — builds the index from songs.json
- `public/data/index.json` — the built index (committed to git, loaded by the browser)
- `src/lib/tokenize.ts` — the TypeScript tokenizer (must match Python version)
- `src/types/index.ts` — TypeScript type definitions for the index structure
