# Liner Labs

A fast, searchable lyrics database with phrase-based search powered by an inverted index. Browse and explore lyrics across your favorite artists with album filtering and dark mode support.

## Features

- **Instant Search** — Find lyrics with phrase search using an inverted index for performance
- **Album Filtering** — Narrow results to specific albums
- **Dark Mode** — Toggle between light and dark themes with persistent preference
- **Responsive Design** — Works seamlessly on desktop and mobile
- **Artist Browsing** — Browse multiple artists with album art mosaics

## Tech Stack

- **React 19** with TypeScript
- **React Router v7** for client-side routing
- **Vite** for fast development and builds
- **Tailwind CSS** for styling
- **Inverted Index** for efficient full-text search

## Project Structure

```
src/
├── pages/              # Route pages (Home, Search)
├── components/         # Reusable UI components
├── hooks/              # Custom React hooks (useSearch)
├── lib/                # Utilities (tokenize, search)
├── types/              # TypeScript interfaces
└── index.css           # Global styles
```

## Getting Started

### Prerequisites
- Node.js 18+

### Installation

```bash
npm install
```

### Development

```bash
npm run dev
```

Open [http://localhost:5173](http://localhost:5173) in your browser.

### Build

```bash
npm run build
```

### Preview Production Build

```bash
npm run preview
```

## Data Format

The app expects artist data in `/public/data/`:

```
public/data/
├── artists.json              # List of artists with paths
├── artist-name/
│   ├── songs.json           # Song metadata with lyrics
│   └── index.json           # Pre-built inverted index
```

### artists.json
```json
[
  {
    "slug": "artist-slug",
    "name": "Artist Name",
    "songsPath": "/data/artist-name/songs.json",
    "indexPath": "/data/artist-name/index.json"
  }
]
```

### songs.json
```json
[
  {
    "id": 1,
    "title": "Song Title",
    "album": "Album Name",
    "year": 2023,
    "albumArt": "https://image-url.jpg",
    "lines": ["Lyric line 1", "Lyric line 2", ...]
  }
]
```

### index.json (Inverted Index)
```json
{
  "token": {
    "songId": [[lineIndex, wordIndex], ...]
  }
}
```

## Search Algorithm

The search uses an inverted index built from tokenized lyrics:

1. **Tokenization** — Normalize text to lowercase, split by whitespace, remove punctuation
2. **Indexing** — Map each token to positions `[lineIndex, wordIndex]` where it appears
3. **Query Processing** — Handle phrase search by verifying token adjacency
4. **Filtering** — Optional album filter applied to results

See `src/lib/search.ts` and `src/lib/tokenize.ts` for implementation details.

## Theme Persistence

Theme preference is saved to `localStorage` under the key `theme`. Defaults to system preference if not set.

## Linting

```bash
npm run lint
```

## License

MIT
