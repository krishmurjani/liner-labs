import { useState, useEffect } from 'react'
import { SearchBar } from './components/SearchBar'
import { ResultsList } from './components/ResultsList'
import { ThemeToggle } from './components/ThemeToggle'
import { AlbumFilter, albumsFromSongs } from './components/AlbumFilter'
import { useSearch } from './hooks/useSearch'
import type { IndexData, SongMeta } from './types'

function getInitialTheme(): 'dark' | 'light' {
  const stored = localStorage.getItem('theme')
  if (stored === 'dark' || stored === 'light') return stored
  return window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light'
}

export default function App() {
  const [theme, setTheme] = useState<'dark' | 'light'>(getInitialTheme)
  const [indexData, setIndexData] = useState<IndexData | null>(null)
  const [loadError, setLoadError] = useState<string | null>(null)
  const [query, setQuery] = useState('')
  const [selectedAlbums, setSelectedAlbums] = useState<Set<string>>(new Set())
  const [showFilters, setShowFilters] = useState(false)

  // Apply theme class to <html> whenever theme changes
  useEffect(() => {
    const root = document.documentElement
    if (theme === 'dark') root.classList.add('dark')
    else root.classList.remove('dark')
    localStorage.setItem('theme', theme)
  }, [theme])

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

  const albumFilter = selectedAlbums.size > 0 ? selectedAlbums : null
  const { results, totalCount, status } = useSearch(indexData, query, albumFilter)

  return (
    <div className="min-h-screen bg-white dark:bg-zinc-950 text-zinc-900 dark:text-zinc-100 transition-colors duration-300">
      <div className="flex flex-col items-center px-4 py-12">
        {/* Theme toggle — top right */}
        <div className="fixed top-4 right-4">
          <ThemeToggle theme={theme} onToggle={() => setTheme(t => t === 'dark' ? 'light' : 'dark')} />
        </div>

        <header className="mb-8 text-center">
          <h1 className="text-3xl font-bold tracking-tight text-zinc-900 dark:text-white">Liner Labs</h1>
          <p className="text-zinc-400 dark:text-zinc-500 mt-1 text-sm">
            Bleachers lyrics · {indexData ? `${indexData.songs.length} songs` : 'loading…'}
          </p>
        </header>

        <main className="w-full max-w-2xl space-y-6">
          {loadError ? (
            <p className="text-red-500 text-sm text-center">{loadError}</p>
          ) : (
            <>
              <div className="space-y-3">
                <div className="flex items-center gap-2">
                  <SearchBar value={query} onChange={setQuery} disabled={!indexData} />
                  {indexData && (
                    <button
                      onClick={() => setShowFilters(v => !v)}
                      className={`shrink-0 flex items-center gap-1.5 px-3 py-3 rounded-xl border text-xs
                                  transition-colors duration-150
                                  ${showFilters || selectedAlbums.size > 0
                                    ? 'border-zinc-400 dark:border-zinc-400 bg-zinc-200 dark:bg-zinc-700 text-zinc-900 dark:text-zinc-100'
                                    : 'border-zinc-300 dark:border-zinc-700 text-zinc-400 dark:text-zinc-500 hover:border-zinc-400 dark:hover:border-zinc-500 hover:text-zinc-700 dark:hover:text-zinc-300'
                                  }`}
                    >
                      <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                        <line x1="4" y1="6" x2="20" y2="6" /><line x1="8" y1="12" x2="16" y2="12" /><line x1="11" y1="18" x2="13" y2="18" />
                      </svg>
                      {selectedAlbums.size > 0 ? `${selectedAlbums.size}` : 'Filter'}
                    </button>
                  )}
                </div>
                {showFilters && indexData && (
                  <AlbumFilter
                    albums={albumsFromSongs(indexData.songs)}
                    selected={selectedAlbums}
                    onChange={setSelectedAlbums}
                  />
                )}
              </div>
              <ResultsList results={results} totalCount={totalCount} status={status} query={query} />
            </>
          )}
        </main>
      </div>
    </div>
  )
}
