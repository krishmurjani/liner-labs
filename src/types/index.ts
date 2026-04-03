// A single song with its metadata and lyrics split into lines.
export interface SongMeta {
  id: number
  title: string
  album: string
  year: number
  albumArt?: string
  lines: string[]
}

// A position in the lyrics: [lineIndex, wordIndex].
// Both are zero-based. Used by the inverted index to record exactly
// where each word appears so phrase search can verify adjacency.
export type Position = [number, number]

// The posting map for a single token:
// maps song ID (as string) → list of positions where that token appears.
export type PostingMap = Record<string, Position[]>

// The full inverted index: maps each token → its PostingMap.
export type InvertedIndex = Record<string, PostingMap>

// Everything the app needs after loading the JSON files.
export interface IndexData {
  songs: SongMeta[]
  songsById: Record<string, SongMeta>
  index: InvertedIndex
}

// One search result: a song that matched the query, plus which lines matched.
export interface SearchResult {
  song: SongMeta
  matchedLineIndices: number[]
  // Each entry is [lineIndex, wordIndex] pointing to the start of a match.
  positions: Position[]
}
