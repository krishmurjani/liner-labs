import { useState, useEffect } from 'react'
import { SearchBar } from './components/SearchBar'
import { ResultsList } from './components/ResultsList'
import { useSearch } from './hooks/useSearch'
import type { IndexData, SongMeta } from './types'

export default function App() {
  const [indexData, setIndexData] = useState<IndexData | null>(null)
  const [loadError, setLoadError] = useState<string | null>(null)
  const [query, setQuery] = useState('')

  // Load songs.json and index.json in parallel on mount.
  // They live in public/data/ and are served as static files — no server needed.
  useEffect(() => {
    Promise.all([
      fetch('/data/songs.json').then(r => r.json()),
      fetch('/data/index.json').then(r => r.json()),
    ])
      .then(([songs, index]: [SongMeta[], IndexData['index']]) => {
        const songsById: IndexData['songsById'] = {}
        for (const s of songs) songsById[String(s.id)] = s
        setIndexData({ songs, songsById, index })
      })
      .catch(() =>
        setLoadError('Failed to load index. Run the data pipeline first (see scripts/).')
      )
  }, [])

  const { results, totalCount, status } = useSearch(indexData, query, null)

  return (
    <div className="min-h-screen bg-zinc-950 text-zinc-100 flex flex-col items-center px-4 py-12">
      <header className="mb-8 text-center">
        <h1 className="text-3xl font-bold tracking-tight text-white">Liner Labs</h1>
        <p className="text-zinc-500 mt-1 text-sm">Bleachers lyrics · {indexData ? `${indexData.songs.length} songs` : 'loading…'}</p>
      </header>

      <main className="w-full max-w-2xl space-y-6">
        {loadError ? (
          <p className="text-red-400 text-sm text-center">{loadError}</p>
        ) : (
          <>
            <SearchBar
              value={query}
              onChange={setQuery}
              disabled={!indexData}
            />
            <ResultsList
              results={results}
              totalCount={totalCount}
              status={status}
              query={query}
            />
          </>
        )}
      </main>
    </div>
  )
}
