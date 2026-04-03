import { useState, useEffect, useRef } from 'react'
import { search } from '../lib/search'
import type { IndexData, SearchResult } from '../types'

export type SearchStatus = 'idle' | 'done'

interface UseSearchResult {
  results: SearchResult[]
  totalCount: number
  status: SearchStatus
}

/**
 * Custom hook that runs the search algorithm whenever the query or album
 * filter changes, with a 200ms debounce on the query.
 *
 * Debouncing means: don't search on every single keystroke. Wait until the
 * user has stopped typing for 200ms, then search. This avoids running the
 * algorithm ~10 times while someone types "wanna get better".
 *
 * The search itself is so fast (<1ms) that debouncing is more about avoiding
 * unnecessary re-renders than actual performance — but it's good practice.
 */
export function useSearch(
  indexData: IndexData | null,
  rawQuery: string,
  albumFilter: Set<string> | null,
): UseSearchResult {
  const [results, setResults] = useState<SearchResult[]>([])
  const [totalCount, setTotalCount] = useState(0)
  const [status, setStatus] = useState<SearchStatus>('idle')
  const debounceTimer = useRef<ReturnType<typeof setTimeout> | null>(null)

  useEffect(() => {
    // Clear any pending debounce
    if (debounceTimer.current) clearTimeout(debounceTimer.current)

    if (!indexData || rawQuery.trim() === '') {
      setResults([])
      setTotalCount(0)
      setStatus('idle')
      return
    }

    debounceTimer.current = setTimeout(() => {
      const { results: r, totalCount: t } = search(rawQuery, indexData, albumFilter)
      setResults(r)
      setTotalCount(t)
      setStatus('done')
    }, 200)

    return () => {
      if (debounceTimer.current) clearTimeout(debounceTimer.current)
    }
  }, [indexData, rawQuery, albumFilter])

  return { results, totalCount, status }
}
