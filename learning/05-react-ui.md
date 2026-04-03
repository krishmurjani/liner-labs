# 05 — React UI

## What was built
The full search interface: a text input, results list, individual result cards with highlighted matching lines, and the plumbing that connects them to the search algorithm.

---

## How React works (one-paragraph version)

React is a library for building UIs as a tree of **components** — functions that return HTML-like descriptions of what to show. When data changes, React figures out the minimum set of DOM updates needed and applies them. You describe _what_ the UI should look like for a given state; React handles _how_ to get there.

---

## Component tree

```
App
├── SearchBar          ← controlled input
└── ResultsList
    └── ResultCard[]   ← one per matching song
        └── HighlightedLine[]  ← one per matched lyric line
```

**Data flows down** (parent → child via props). **Events flow up** (child calls a callback the parent gave it).

---

## State: where things live and why

| State | Lives in | Why |
|---|---|---|
| `indexData` | `App` | Loaded once; every component needs songs/index |
| `query` | `App` | Controlled by `SearchBar`, consumed by `useSearch` |
| `results`, `status` | `useSearch` hook | Search output; derived from query + index |

`SearchBar` has no state — it's a "controlled component". Its value comes from `App` as a prop, and it calls `onChange` (also a prop) when the user types. The parent owns the value; the input just displays it.

This pattern prevents the state from being split in two places. If `SearchBar` owned its own value, you'd have to keep it in sync with `App` — fragile.

---

## useSearch — the custom hook

```typescript
const { results, totalCount, status } = useSearch(indexData, query, albumFilter)
```

A custom hook is just a function that uses React's built-in hooks (`useState`, `useEffect`) and packages them up for reuse. It lets you extract stateful logic out of components.

`useSearch` does two things:
1. **Debouncing**: uses `setTimeout` to wait 200ms after the query changes before running the search. If the query changes again within 200ms (user still typing), the timer resets. This prevents running the search algorithm on every single keystroke.
2. **Running the search**: calls `search(rawQuery, indexData, albumFilter)` from `src/lib/search.ts` and stores the result in state.

### What is `useEffect`?
`useEffect` runs side effects — code that happens in response to state or prop changes, outside of rendering. Here it runs the debounced search whenever `query`, `indexData`, or `albumFilter` change.

The cleanup function (`return () => clearTimeout(...)`) cancels the pending timer if the component unmounts or the dependencies change before the timer fires.

---

## HighlightedLine — the tricky one

This component receives a raw lyric line (like `"I didn't know I was broken"`) and highlights the matched word(s).

Why not just do `line.replace("didnt", "<mark>didnt</mark>")`?

Because the raw line has `"didn't"` (with apostrophe) but the query token is `"didnt"` (apostrophe stripped). A string replace of `"didnt"` won't find `"didn't"`.

**The solution**: tokenize the raw line character-by-character, tracking where each word starts and ends in the original string. Then match those positions against the query tokens.

```
Input line:   "I didn't know"
              ^0          ^12
Character walk:
  "I"      → token "i",     charRange [0, 1]
  "didn't" → token "didnt", charRange [2, 9]
  "know"   → token "know",  charRange [10, 14]

Query: "didnt"
Match: span at charRange [2, 9] → original text "didn't" → wrap in <mark>
```

Result: `"I "` + `<mark>didn't</mark>` + `" know"` — the display shows the original apostrophe, but matching worked on the normalized token.

---

## Why `font-mono` on lyric lines?

Monospace font makes every character the same width, which keeps lyric lines visually stable as highlighted spans are applied. Variable-width fonts can cause text to shift when `<mark>` elements change inline layout.

---

## Loading strategy

```typescript
Promise.all([
  fetch('/data/songs.json').then(r => r.json()),
  fetch('/data/index.json').then(r => r.json()),
]).then(([songs, index]) => { ... })
```

`Promise.all` fires both fetches simultaneously and waits for both to finish. If they were fetched sequentially (`await fetch songs`, then `await fetch index`), total time would be the sum. In parallel, it's the max — roughly halving load time.

---

## The `disabled` search bar

While the index is loading (`indexData === null`), `SearchBar` receives `disabled={true}`. This prevents the user from typing a query before there's anything to search. The placeholder text reads "loading…" via the header subtitle rather than disabling the input itself — the input is visually dimmed by Tailwind's `disabled:opacity-40`.

---

## Key files
- `src/App.tsx` — root component, data loading, state ownership
- `src/hooks/useSearch.ts` — debounce + search dispatch
- `src/components/SearchBar.tsx` — controlled input
- `src/components/ResultsList.tsx` — status/results display
- `src/components/ResultCard.tsx` — per-song result
- `src/components/HighlightedLine.tsx` — char-offset highlighting
