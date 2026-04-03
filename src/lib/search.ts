import { tokenize } from './tokenize'
import type { IndexData, SearchResult, Position } from '../types'

// Maximum results shown to the user. Prevents UI overload on common words.
const MAX_RESULTS = 50

/**
 * Search for a single word in the index.
 * O(1) — just a hash lookup, then filter + sort.
 */
function searchSingleWord(
  token: string,
  data: IndexData,
  albumFilter: string | null,
): SearchResult[] {
  const postingMap = data.index[token]
  if (!postingMap) return []

  const results: SearchResult[] = []

  for (const songId of Object.keys(postingMap)) {
    const song = data.songsById[songId]
    if (!song) continue
    if (albumFilter && song.album !== albumFilter) continue

    const positions = postingMap[songId]

    // Collect unique line indices that contain this word
    const lineSet = new Set<number>()
    for (const [lineIdx] of positions) lineSet.add(lineIdx)

    results.push({
      song,
      matchedLineIndices: Array.from(lineSet).sort((a, b) => a - b),
      positions,
    })
  }

  return results
}

/**
 * Search for a multi-word phrase using positional intersection.
 *
 * How it works:
 *   1. Look up every token in the index. If any token is missing, no match possible.
 *   2. Find songs that appear in ALL posting maps (candidates for phrase match).
 *   3. For each candidate song, use the first token's positions as "anchors".
 *      For each anchor [lineIdx, wordIdx], check if the subsequent tokens appear
 *      at [lineIdx, wordIdx+1], [lineIdx, wordIdx+2], etc.
 *   4. Checking adjacency is O(1) per lookup using pre-built Sets.
 *
 * Phrase cannot span lines — both words must be on the same line.
 */
function searchPhrase(
  tokens: string[],
  data: IndexData,
  albumFilter: string | null,
): SearchResult[] {
  // Step 1: get posting maps for all tokens; bail early if any is missing
  const postingMaps = tokens.map(t => data.index[t])
  if (postingMaps.some(pm => !pm)) return []

  // Step 2: candidate songs must appear in every posting map
  const songSets = postingMaps.map(pm => new Set(Object.keys(pm)))
  // Start from the smallest set for efficiency
  const [smallest, ...rest] = songSets.sort((a, b) => a.size - b.size)
  const candidateSongIds = Array.from(smallest).filter(id =>
    rest.every(set => set.has(id)),
  )

  const results: SearchResult[] = []

  for (const songId of candidateSongIds) {
    const song = data.songsById[songId]
    if (!song) continue
    if (albumFilter && song.album !== albumFilter) continue

    // Step 3: pre-build position Sets for tokens 1..N (O(1) lookup per check)
    // Key format: "lineIdx,wordIdx"
    const positionSets = postingMaps.slice(1).map(pm => {
      const set = new Set<string>()
      for (const [l, w] of (pm[songId] ?? [])) set.add(`${l},${w}`)
      return set
    })

    // Step 4: try each anchor from the first token
    const phraseMatches: Position[] = []
    for (const [lineIdx, wordIdx] of postingMaps[0][songId]) {
      let isPhrase = true
      for (let i = 0; i < positionSets.length; i++) {
        if (!positionSets[i].has(`${lineIdx},${wordIdx + i + 1}`)) {
          isPhrase = false
          break
        }
      }
      if (isPhrase) phraseMatches.push([lineIdx, wordIdx])
    }

    if (phraseMatches.length > 0) {
      const lineSet = new Set(phraseMatches.map(([l]) => l))
      results.push({
        song,
        matchedLineIndices: Array.from(lineSet).sort((a, b) => a - b),
        positions: phraseMatches,
      })
    }
  }

  return results
}

/**
 * Main search entry point.
 * Tokenizes the query, dispatches to single-word or phrase search,
 * sorts results by album year then song title.
 */
export function search(
  rawQuery: string,
  data: IndexData,
  albumFilter: string | null = null,
): { results: SearchResult[]; totalCount: number } {
  const tokens = tokenize(rawQuery)
  if (tokens.length === 0) return { results: [], totalCount: 0 }

  const all =
    tokens.length === 1
      ? searchSingleWord(tokens[0], data, albumFilter)
      : searchPhrase(tokens, data, albumFilter)

  // Sort by year ascending, then alphabetically by title
  all.sort((a, b) =>
    a.song.year !== b.song.year
      ? a.song.year - b.song.year
      : a.song.title.localeCompare(b.song.title),
  )

  return {
    results: all.slice(0, MAX_RESULTS),
    totalCount: all.length,
  }
}
