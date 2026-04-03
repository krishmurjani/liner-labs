import { ResultCard } from './ResultCard'
import type { SearchResult } from '../types'
import type { SearchStatus } from '../hooks/useSearch'

interface Props {
  results: SearchResult[]
  totalCount: number
  status: SearchStatus
  query: string
}

export function ResultsList({ results, totalCount, status, query }: Props) {
  if (status === 'idle') {
    return (
      <p className="text-center text-zinc-600 text-sm mt-8">
        Type a word or phrase to search the lyrics
      </p>
    )
  }

  if (results.length === 0) {
    return (
      <p className="text-center text-zinc-500 text-sm mt-8">
        No matches for <span className="text-zinc-300 font-mono">"{query}"</span>
      </p>
    )
  }

  return (
    <div className="space-y-3">
      <p className="text-zinc-500 text-xs">
        {totalCount > results.length
          ? `Showing ${results.length} of ${totalCount} matches — try a more specific phrase`
          : `${totalCount} match${totalCount !== 1 ? 'es' : ''}`}
      </p>
      {results.map(r => (
        <ResultCard key={r.song.id} result={r} query={query} />
      ))}
    </div>
  )
}
