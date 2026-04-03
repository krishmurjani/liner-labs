# 04 — Search Algorithm

## What was built
The search logic in `src/lib/search.ts` — two functions that run entirely in the browser:
- `searchSingleWord()` for one-word queries
- `searchPhrase()` for multi-word queries

---

## Single-word search — O(1)

For a query like `"better"`:

```
1. Tokenize "better" → ["better"]
2. Look up index["better"]  ← one hash map lookup, instant
3. For each song in the result:
     - skip if album filter doesn't match
     - collect unique line indices
4. Sort results by year, then title
5. Return top 50
```

A hash map (JavaScript object) stores keys in a way that lets you jump directly to any entry without scanning. Think of it like a dictionary — finding "better" doesn't require reading A through Q first. That's what O(1) means: constant time, regardless of how many words are in the index.

---

## Phrase search — positional intersection

For a query like `"i wanna get better"`, tokenized to `["i", "wanna", "get", "better"]`:

### Step 1: Check all tokens exist
```
if index["i"] is missing → return [] immediately
if index["wanna"] is missing → return [] immediately
if index["get"] is missing → return [] immediately
if index["better"] is missing → return [] immediately
```
If any word doesn't exist anywhere in the lyrics, the phrase can't exist.

### Step 2: Find candidate songs
The phrase can only appear in songs that contain **all** of the words. So:
```
songs_with_i      = { 390927, 339923, ... }  ← 54 songs probably
songs_with_wanna  = { 390927, 701041, ... }  ← fewer songs
songs_with_get    = { 390927, 339923, ... }  ← some songs
songs_with_better = { 390927, ... }          ← fewer still

candidates = intersection of all four sets
           = { 390927 }  ← only songs that have all four words
```
Start with the smallest set for efficiency — fewer songs to check.

### Step 3: Verify phrase adjacency for each candidate
For song `390927`, look at every position where "i" appears (the first token, used as "anchors"):

```
"i" at [1, 0]:
  check: is "wanna" at [1, 1]?  → yes ✓
  check: is "get" at [1, 2]?    → yes ✓
  check: is "better" at [1, 3]? → yes ✓
  → PHRASE MATCH at line 1, starting at word 0

"i" at [4, 0]:
  check: is "wanna" at [4, 1]?  → yes ✓
  check: is "get" at [4, 2]?    → yes ✓
  check: is "better" at [4, 3]? → yes ✓
  → PHRASE MATCH at line 4, starting at word 0

"i" at [12, 3]:
  check: is "wanna" at [12, 4]? → no ✗
  → not a phrase match here
```

### The O(1) adjacency check trick

The naive way to check "is 'wanna' at position [1, 4]?" would be to loop through all of "wanna"'s positions and look for [1, 4]. That's O(P) where P is the number of "wanna" positions.

We avoid this by pre-converting each token's position list into a **Set** keyed by `"lineIdx,wordIdx"`:

```
wanna_positions_as_set = Set { "1,1", "4,1", "7,2", ... }
```

Checking `wanna_positions_as_set.has("1,1")` is O(1). We pay the cost of building these Sets once per search, then every adjacency check is instant.

Without this: checking a 3-word phrase over 50 anchor positions would be O(50 × P × P) — could be thousands of comparisons. With pre-built Sets: O(50 × 2) — just 100 comparisons.

### Phrase cannot span lines
The check requires `lineIdx` to match exactly. "wanna" at the end of line 3 and "get" at the start of line 4 will not match — they're at different line indices. This is correct: a phrase is defined as consecutive words on the same line.

---

## The full function signature

```typescript
search(rawQuery, data, albumFilter) → { results, totalCount }
```

- `rawQuery`: whatever the user typed — not pre-processed
- `data`: the loaded index + song list (lives in memory after first load)
- `albumFilter`: null (show all) or an album name string
- Returns: up to 50 results + the total count (so UI can show "showing 50 of 87")

---

## Edge cases handled

**Empty query**: `tokenize("")` returns `[]`. Length check returns early — shows nothing, no "no results" message.

**One-character query**: treated as single-word search. Works correctly.

**Very common words**: "i" appears in ~every song. The result cap of 50 kicks in. `totalCount` is returned so the UI can show "Showing 50 of 54 results — try a more specific phrase."

**Missing word in phrase**: if the index has no entry for one of the tokens, the phrase is impossible and we return immediately without searching further.

**Album filter with phrase**: album filtering happens inside `searchPhrase()` per candidate song, after position intersection. If you add a filter after typing a phrase, the positions are re-checked only for matching-album songs.

---

## Key files
- `src/lib/search.ts` — the search algorithm
- `src/lib/tokenize.ts` — the tokenizer (called at the start of every search)
- `src/types/index.ts` — type definitions used throughout
