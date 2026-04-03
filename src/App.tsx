import { useState, useEffect } from 'react'
import { SearchBar } from './components/SearchBar'
import { ResultsList } from './components/ResultsList'
import { ThemeToggle } from './components/ThemeToggle'
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

  const { results, totalCount, status } = useSearch(indexData, query, null)

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
              <SearchBar value={query} onChange={setQuery} disabled={!indexData} />
              <ResultsList results={results} totalCount={totalCount} status={status} query={query} />
            </>
          )}
        </main>
      </div>
    </div>
  )
}
