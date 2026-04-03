import { useState, useEffect } from 'react'
import { ResultCard } from './ResultCard'
import type { SearchResult } from '../types'
import type { SearchStatus } from '../hooks/useSearch'

const PAGE_SIZE = 10

interface Props {
  results: SearchResult[]
  totalCount: number
  status: SearchStatus
  query: string
}

export function ResultsList({ results, totalCount, status, query }: Props) {
  const [page, setPage] = useState(1)

  // Reset to page 1 whenever results change
  useEffect(() => { setPage(1) }, [results])

  if (status === 'idle') {
    return (
      <p className="text-center text-zinc-400 dark:text-zinc-600 text-sm mt-8">
        Type a word or phrase to search the lyrics
      </p>
    )
  }

  if (results.length === 0) {
    return (
      <p className="text-center text-zinc-500 text-sm mt-8">
        No matches for <span className="text-zinc-700 dark:text-zinc-300 font-mono">"{query}"</span>
      </p>
    )
  }

  const totalPages = Math.ceil(results.length / PAGE_SIZE)
  const pageResults = results.slice((page - 1) * PAGE_SIZE, page * PAGE_SIZE)

  return (
    <div className="space-y-3">
      <p className="text-zinc-400 dark:text-zinc-500 text-xs">
        {totalCount > results.length
          ? `Showing ${results.length} of ${totalCount} — try a more specific phrase`
          : `${totalCount} match${totalCount !== 1 ? 'es' : ''}`}
      </p>

      {pageResults.map(r => (
        <ResultCard key={r.song.id} result={r} query={query} />
      ))}

      {totalPages > 1 && (
        <div className="flex items-center justify-between pt-2">
          <button
            onClick={() => { setPage(p => p - 1); window.scrollTo({ top: 0, behavior: 'smooth' }) }}
            disabled={page === 1}
            className="px-3 py-1.5 text-xs rounded-lg border
                       border-zinc-200 dark:border-zinc-700
                       text-zinc-600 dark:text-zinc-400
                       hover:border-zinc-400 dark:hover:border-zinc-500
                       disabled:opacity-30 disabled:cursor-not-allowed
                       transition-colors"
          >
            ← Previous
          </button>

          <span className="text-xs text-zinc-400 dark:text-zinc-500">
            Page {page} of {totalPages}
          </span>

          <button
            onClick={() => { setPage(p => p + 1); window.scrollTo({ top: 0, behavior: 'smooth' }) }}
            disabled={page === totalPages}
            className="px-3 py-1.5 text-xs rounded-lg border
                       border-zinc-200 dark:border-zinc-700
                       text-zinc-600 dark:text-zinc-400
                       hover:border-zinc-400 dark:hover:border-zinc-500
                       disabled:opacity-30 disabled:cursor-not-allowed
                       transition-colors"
          >
            Next →
          </button>
        </div>
      )}
    </div>
  )
}
