import { tokenize } from './tokenize'
import type { IndexData, SearchResult, Position } from '../types'

const MAX_RESULTS = 500

function albumMatches(album: string, filter: Set<string> | null): boolean {
  return !filter || filter.size === 0 || filter.has(album)
}

function searchSingleWord(
  token: string,
  data: IndexData,
  albumFilter: Set<string> | null,
): SearchResult[] {
  const postingMap = data.index[token]
  if (!postingMap) return []

  const results: SearchResult[] = []
  for (const songId of Object.keys(postingMap)) {
    const song = data.songsById[songId]
    if (!song || !albumMatches(song.album, albumFilter)) continue
    const positions = postingMap[songId]
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

function searchPhrase(
  tokens: string[],
  data: IndexData,
  albumFilter: Set<string> | null,
): SearchResult[] {
  const postingMaps = tokens.map(t => data.index[t])
  if (postingMaps.some(pm => !pm)) return []

  const songSets = postingMaps.map(pm => new Set(Object.keys(pm)))
  const [smallest, ...rest] = songSets.sort((a, b) => a.size - b.size)
  const candidateSongIds = Array.from(smallest).filter(id =>
    rest.every(set => set.has(id)),
  )

  const results: SearchResult[] = []
  for (const songId of candidateSongIds) {
    const song = data.songsById[songId]
    if (!song || !albumMatches(song.album, albumFilter)) continue

    const positionSets = postingMaps.slice(1).map(pm => {
      const set = new Set<string>()
      for (const [l, w] of (pm[songId] ?? [])) set.add(`${l},${w}`)
      return set
    })

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

export function search(
  rawQuery: string,
  data: IndexData,
  albumFilter: Set<string> | null = null,
): { results: SearchResult[]; totalCount: number } {
  const tokens = tokenize(rawQuery)
  if (tokens.length === 0) return { results: [], totalCount: 0 }

  const all =
    tokens.length === 1
      ? searchSingleWord(tokens[0], data, albumFilter)
      : searchPhrase(tokens, data, albumFilter)

  all.sort((a, b) =>
    a.song.year !== b.song.year
      ? a.song.year - b.song.year
      : a.song.title.localeCompare(b.song.title),
  )

  return { results: all.slice(0, MAX_RESULTS), totalCount: all.length }
}
