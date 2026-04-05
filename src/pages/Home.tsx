import { useEffect, useState, useRef } from 'react'
import { useNavigate } from 'react-router-dom'
import { Navbar } from '../components/Navbar'
import { ResultsList } from '../components/ResultsList'
import { SearchBar } from '../components/SearchBar'
import { useSearch } from '../hooks/useSearch'
import type { Artist, IndexData, SongMeta } from '../types'

interface ArtistCardData extends Artist {
  songCount: number
  albumCovers: string[]   // up to 4 unique album art URLs, for the mosaic
  albums: string[]
}

interface LoadedArtistData {
  artist: Artist
  songs: SongMeta[]
  index: IndexData['index'] | null
}

interface Props {
  theme: 'dark' | 'light'
  onToggleTheme: () => void
}

export default function Home({ theme, onToggleTheme }: Props) {
  const [artists, setArtists] = useState<ArtistCardData[]>([])
  const [megaArtistCount, setMegaArtistCount] = useState(0)
  const [megaIndexData, setMegaIndexData] = useState<IndexData | null>(null)
  const [megaQuery, setMegaQuery] = useState('')
  const [megaError, setMegaError] = useState<string | null>(null)
  const [draggedIndex, setDraggedIndex] = useState<number | null>(null)
  const [viewMode, setViewMode] = useState<'card' | 'list'>('card')
  const [reorderMode, setReorderMode] = useState(false)
  const listContainerRef = useRef<HTMLDivElement>(null)
  const scrollAnimationRef = useRef<number | null>(null)
  const touchDragRef = useRef<{
    dragIndex: number
    overIndex: number | null
    ghost: HTMLElement | null
    offsetX: number
    offsetY: number
  } | null>(null)
  const navigate = useNavigate()
  const { results, totalCount, status } = useSearch(megaIndexData, megaQuery, null)

  const handleTouchStart = (e: React.TouchEvent<HTMLElement>, index: number) => {
    if (!reorderMode) return
    e.stopPropagation()
    const touch = e.touches[0]
    const el = e.currentTarget
    const rect = el.getBoundingClientRect()

    // Clone the element as a ghost
    const ghost = el.cloneNode(true) as HTMLElement
    ghost.style.position = 'fixed'
    ghost.style.left = rect.left + 'px'
    ghost.style.top = rect.top + 'px'
    ghost.style.width = rect.width + 'px'
    ghost.style.opacity = '0.9'
    ghost.style.pointerEvents = 'none'
    ghost.style.zIndex = '9999'
    ghost.style.transform = 'scale(1.03)'
    ghost.style.boxShadow = '0 8px 30px rgba(0,0,0,0.3)'
    ghost.style.transition = 'none'
    ghost.style.borderRadius = '0.5rem'
    document.body.appendChild(ghost)

    touchDragRef.current = {
      dragIndex: index,
      overIndex: null,
      ghost,
      offsetX: touch.clientX - rect.left,
      offsetY: touch.clientY - rect.top,
    }

    setDraggedIndex(index)
  }

  const handleTouchMove = (e: React.TouchEvent<HTMLElement>) => {
    if (!reorderMode || !touchDragRef.current) return
    e.preventDefault()
    const touch = e.touches[0]
    const { ghost, offsetX, offsetY } = touchDragRef.current

    // Move ghost
    if (ghost) {
      ghost.style.left = (touch.clientX - offsetX) + 'px'
      ghost.style.top = (touch.clientY - offsetY) + 'px'
    }

    // Auto-scroll list container near edges
    const container = listContainerRef.current
    if (container) {
      const rect = container.getBoundingClientRect()
      const scrollZone = 60
      const maxSpeed = 10
      if (scrollAnimationRef.current) {
        cancelAnimationFrame(scrollAnimationRef.current)
        scrollAnimationRef.current = null
      }
      const distToBottom = rect.bottom - touch.clientY
      const distToTop = touch.clientY - rect.top
      const scroll = () => {
        let delta = 0
        if (distToBottom < scrollZone && distToBottom > 0) delta = (1 - distToBottom / scrollZone) * maxSpeed
        else if (distToTop < scrollZone && distToTop > 0) delta = -(1 - distToTop / scrollZone) * maxSpeed
        if (delta !== 0) { container.scrollTop += delta; scrollAnimationRef.current = requestAnimationFrame(scroll) }
      }
      if (distToBottom < scrollZone || distToTop < scrollZone) {
        scrollAnimationRef.current = requestAnimationFrame(scroll)
      }
    }

    // Find which item is under the finger
    if (ghost) ghost.style.display = 'none'
    const el = document.elementFromPoint(touch.clientX, touch.clientY)
    if (ghost) ghost.style.display = ''

    const target = el?.closest('[data-drag-index]')
    const overIndex = target ? parseInt(target.getAttribute('data-drag-index')!, 10) : null
    touchDragRef.current.overIndex = overIndex
  }

  const handleTouchEnd = () => {
    if (!touchDragRef.current) return
    const { dragIndex, overIndex, ghost } = touchDragRef.current

    if (ghost) ghost.remove()
    if (scrollAnimationRef.current) {
      cancelAnimationFrame(scrollAnimationRef.current)
      scrollAnimationRef.current = null
    }

    if (overIndex !== null && overIndex !== dragIndex) {
      const newArtists = [...artists]
      const [moved] = newArtists.splice(dragIndex, 1)
      newArtists.splice(overIndex, 0, moved)
      setArtists(newArtists)
      localStorage.setItem('artistOrder', JSON.stringify(newArtists.map(a => a.slug)))
    }

    touchDragRef.current = null
    setDraggedIndex(null)
  }

  // Auto-scroll during drag using requestAnimationFrame
  const handleDragOver = (e: React.DragEvent<HTMLDivElement>) => {
    if (!reorderMode || !listContainerRef.current) return

    const container = listContainerRef.current
    const rect = container.getBoundingClientRect()
    const scrollZone = 60
    const maxScrollSpeed = 10

    // Calculate distance from edges
    const distToBottom = rect.bottom - e.clientY
    const distToTop = e.clientY - rect.top

    // Function to perform smooth scroll
    const scroll = () => {
      let scrollDelta = 0

      if (distToBottom < scrollZone && distToBottom > 0) {
        // Near bottom: scroll proportionally faster the closer to edge
        const intensity = 1 - distToBottom / scrollZone
        scrollDelta = intensity * maxScrollSpeed
      } else if (distToTop < scrollZone && distToTop > 0) {
        // Near top: scroll proportionally faster the closer to edge
        const intensity = 1 - distToTop / scrollZone
        scrollDelta = -intensity * maxScrollSpeed
      }

      if (scrollDelta !== 0) {
        container.scrollTop += scrollDelta
        if (scrollAnimationRef.current) {
          scrollAnimationRef.current = requestAnimationFrame(scroll)
        }
      }
    }

    // Start animation if not already running and need to scroll
    if (!scrollAnimationRef.current && (distToBottom < scrollZone || distToTop < scrollZone)) {
      scrollAnimationRef.current = requestAnimationFrame(scroll)
    }
  }

  const handleDragLeave = () => {
    if (scrollAnimationRef.current) {
      cancelAnimationFrame(scrollAnimationRef.current)
      scrollAnimationRef.current = null
    }
  }

  const handleDragEnd = () => {
    if (scrollAnimationRef.current) {
      cancelAnimationFrame(scrollAnimationRef.current)
      scrollAnimationRef.current = null
    }
    setDraggedIndex(null)
  }

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      if (scrollAnimationRef.current) cancelAnimationFrame(scrollAnimationRef.current)
    }
  }, [])

  useEffect(() => {
    let cancelled = false

    fetch('/data/artists.json')
      .then(r => r.json())
      .then(async (list: Artist[]) => {
        const loaded = await Promise.allSettled(list.map(async artist => {
          const songsResponse = await fetch(artist.songsPath)
          if (!songsResponse.ok) throw new Error(`${artist.slug} songs not ready`)
          const songs: SongMeta[] = await songsResponse.json()

          let index: IndexData['index'] | null = null
          try {
            const indexResponse = await fetch(artist.indexPath)
            if (indexResponse.ok) index = await indexResponse.json()
          } catch {
            index = null
          }

          return { artist, songs, index }
        }))

        if (cancelled) return

        const successfulArtists = loaded
          .filter((result): result is PromiseFulfilledResult<LoadedArtistData> => result.status === 'fulfilled')
          .map(result => result.value)

        const cards = successfulArtists.map(({ artist, songs }) => {
          const albumMap = new Map<string, string>()
          for (const song of songs) {
            if (!albumMap.has(song.album) && song.albumArt) albumMap.set(song.album, song.albumArt)
          }
          return {
            ...artist,
            songCount: songs.length,
            albums: Array.from(albumMap.keys()),
            albumCovers: Array.from(albumMap.values()).slice(0, 4),
          }
        })

        // Sort alphabetically by default
        const sortedCards = [...cards].sort((a, b) => a.name.localeCompare(b.name))

        // Apply custom order from localStorage if it exists
        const savedOrder = localStorage.getItem('artistOrder')
        let orderedCards = sortedCards
        if (savedOrder) {
          try {
            const order = JSON.parse(savedOrder) as string[]
            const cardMap = new Map(sortedCards.map(c => [c.slug, c]))
            orderedCards = order
              .map(slug => cardMap.get(slug))
              .filter((c): c is ArtistCardData => c !== undefined)
            // Add any new artists that weren't in saved order
            const orderedSlugs = new Set(orderedCards.map(c => c.slug))
            orderedCards.push(...sortedCards.filter(c => !orderedSlugs.has(c.slug)))
          } catch {
            orderedCards = sortedCards
          }
        }

        setArtists(orderedCards)

        const searchableArtists = successfulArtists.filter(
          (artist): artist is LoadedArtistData & { index: IndexData['index'] } => artist.index !== null,
        )
        setMegaArtistCount(searchableArtists.length)
        setMegaIndexData(searchableArtists.length > 0 ? buildMergedIndexData(searchableArtists) : null)

        const failedArtistCount = loaded.filter(result => result.status === 'rejected').length
        const missingIndexCount = successfulArtists.length - searchableArtists.length
        if (failedArtistCount > 0 || missingIndexCount > 0) {
          setMegaError('Mega search loaded with some artist data missing.')
        } else {
          setMegaError(null)
        }
      })
      .catch(() => {
        if (cancelled) return
        setArtists([])
        setMegaArtistCount(0)
        setMegaIndexData(null)
        setMegaError('Failed to load artist data.')
      })

    return () => {
      cancelled = true
    }
  }, [])

  return (
    <div className="min-h-screen bg-white dark:bg-zinc-950 text-zinc-900 dark:text-zinc-100">
      <Navbar theme={theme} onToggle={onToggleTheme} />
      <div className="max-w-3xl mx-auto px-4 py-6 space-y-8">
        <header className="space-y-1">
          <h1 className="text-2xl font-bold tracking-tight text-zinc-900 dark:text-white">
            Search lyrics across every catalog
          </h1>
          <p className="text-zinc-400 dark:text-zinc-500 text-sm">
            Use mega search when you know the line but not the artist.
          </p>
        </header>

        <section
          className="rounded-2xl border border-zinc-200 dark:border-zinc-800
                     bg-zinc-50 dark:bg-zinc-900 p-4 sm:p-5 space-y-4"
        >
          <div className="space-y-1">
            <p className="text-[11px] uppercase tracking-[0.2em] text-zinc-400 dark:text-zinc-500">
              Mega Search
            </p>
            <p className="text-sm text-zinc-500 dark:text-zinc-400">
              {megaIndexData
                ? `${megaArtistCount} artists · ${megaIndexData.songs.length} songs indexed`
                : 'Loading all artist indexes…'}
            </p>
            {megaError && (
              <p className="text-sm text-amber-600 dark:text-amber-400">
                {megaError}
              </p>
            )}
          </div>

          <SearchBar value={megaQuery} onChange={setMegaQuery} disabled={!megaIndexData} />
          <ResultsList results={results} totalCount={totalCount} status={status} query={megaQuery} />
        </section>

        <section className="space-y-4">
          <div className="space-y-3">
            <div className="flex items-start justify-between gap-4">
              <div className="space-y-1">
                <h2 className="text-sm font-semibold text-zinc-900 dark:text-white">Browse Artists</h2>
                <p className="text-zinc-400 dark:text-zinc-500 text-sm">
                  Jump into a single artist catalog.
                </p>
              </div>

              <div className="flex items-center gap-2 flex-shrink-0">
                {/* View Mode Toggle */}
                <div className="inline-flex rounded-lg border border-zinc-200 dark:border-zinc-800 bg-zinc-50 dark:bg-zinc-900 p-1">
                  <button
                    onClick={() => setViewMode('card')}
                    className={`px-3 py-1.5 rounded-md text-xs font-medium transition-all duration-300 ${
                      viewMode === 'card'
                        ? 'bg-white dark:bg-zinc-800 text-zinc-900 dark:text-white shadow-sm'
                        : 'text-zinc-500 dark:text-zinc-400 hover:text-zinc-700 dark:hover:text-zinc-300'
                    }`}
                    title="Card view"
                  >
                    ⊞
                  </button>
                  <button
                    onClick={() => setViewMode('list')}
                    className={`px-3 py-1.5 rounded-md text-xs font-medium transition-all duration-300 ${
                      viewMode === 'list'
                        ? 'bg-white dark:bg-zinc-800 text-zinc-900 dark:text-white shadow-sm'
                        : 'text-zinc-500 dark:text-zinc-400 hover:text-zinc-700 dark:hover:text-zinc-300'
                    }`}
                    title="List view"
                  >
                    ≡
                  </button>
                </div>

                {/* Reorder Button */}
                <button
                  onClick={() => setReorderMode(!reorderMode)}
                  className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-all duration-300 ${
                    reorderMode
                      ? 'bg-blue-500 text-white shadow-md dark:shadow-blue-500/30'
                      : 'bg-zinc-100 dark:bg-zinc-800 text-zinc-700 dark:text-zinc-300 hover:bg-zinc-200 dark:hover:bg-zinc-700'
                  }`}
                  title="Toggle reorder mode"
                >
                  {reorderMode ? '✓ Reordering' : 'Reorder'}
                </button>

                {/* Reset to Ascending */}
                {reorderMode && (
                  <button
                    onClick={() => {
                      const sorted = [...artists].sort((a, b) => a.name.localeCompare(b.name))
                      setArtists(sorted)
                      localStorage.setItem('artistOrder', JSON.stringify(sorted.map(a => a.slug)))
                    }}
                    className="px-3 py-1.5 rounded-lg text-xs font-medium bg-zinc-100 dark:bg-zinc-800 text-zinc-700 dark:text-zinc-300 hover:bg-zinc-200 dark:hover:bg-zinc-700 transition-all duration-300"
                    title="Reset to alphabetical order"
                  >
                    ↑ A-Z
                  </button>
                )}
              </div>
            </div>
          </div>

          {artists.length === 0 ? (
            <p className="text-zinc-400 text-sm">Loading…</p>
          ) : viewMode === 'card' ? (
            <div className={`grid grid-cols-1 sm:grid-cols-2 gap-4 transition-all duration-300`}>
              {artists.map((artist, index) => (
                <div
                  key={artist.slug}
                  data-drag-index={index}
                  className="transition-all duration-300"
                  style={{ animation: 'fadeIn 0.4s ease-out' }}
                  onTouchStart={(e) => handleTouchStart(e, index)}
                  onTouchMove={handleTouchMove}
                  onTouchEnd={handleTouchEnd}
                >
                  <ArtistCard
                    artist={artist}
                    index={index}
                    isDragging={draggedIndex === index}
                    isDraggingDisabled={!reorderMode}
                    onDragStart={() => reorderMode && setDraggedIndex(index)}
                    onDragEnd={() => setDraggedIndex(null)}
                    onDrop={(targetIndex) => {
                      if (!reorderMode || draggedIndex === null || draggedIndex === targetIndex) return
                      const newArtists = [...artists]
                      const [draggedArtist] = newArtists.splice(draggedIndex, 1)
                      newArtists.splice(targetIndex, 0, draggedArtist)
                      setArtists(newArtists)
                      setDraggedIndex(null)
                      localStorage.setItem('artistOrder', JSON.stringify(newArtists.map(a => a.slug)))
                    }}
                    onClick={() => navigate(`/${artist.slug}`)}
                  />
                </div>
              ))}
            </div>
          ) : (
            <div
              ref={listContainerRef}
              className="space-y-2 max-h-[calc(100vh-400px)] overflow-y-auto"
              onDragOver={handleDragOver}
              onDragLeave={handleDragLeave}
            >
              {artists.map((artist, index) => (
                <div
                  key={artist.slug}
                  data-drag-index={index}
                  draggable={reorderMode}
                  onTouchStart={(e) => handleTouchStart(e, index)}
                  onTouchMove={handleTouchMove}
                  onTouchEnd={handleTouchEnd}
                  onDragStart={(e) => {
                    if (reorderMode && e.currentTarget) {
                      e.dataTransfer!.effectAllowed = 'move'
                      e.dataTransfer!.setDragImage(e.currentTarget, e.currentTarget.offsetWidth / 2, e.currentTarget.offsetHeight / 2)
                      setDraggedIndex(index)
                    }
                  }}
                  onDragEnd={handleDragEnd}
                  onDragOver={(e) => {
                    if (reorderMode) {
                      e.preventDefault()
                      e.dataTransfer!.dropEffect = 'move'
                    }
                  }}
                  onDrop={(e) => {
                    if (!reorderMode || draggedIndex === null || draggedIndex === index) return
                    e.preventDefault()
                    const newArtists = [...artists]
                    const [draggedArtist] = newArtists.splice(draggedIndex, 1)
                    newArtists.splice(index, 0, draggedArtist)
                    setArtists(newArtists)
                    setDraggedIndex(null)
                    localStorage.setItem('artistOrder', JSON.stringify(newArtists.map(a => a.slug)))
                  }}
                  className={`p-4 rounded-lg border transition-all duration-300 cursor-pointer group
                    ${draggedIndex === index ? 'opacity-50 scale-95' : 'opacity-100'}
                    ${reorderMode ? 'cursor-move hover:border-blue-400 dark:hover:border-blue-500' : 'cursor-pointer hover:border-zinc-400 dark:hover:border-zinc-600'}
                    border-zinc-200 dark:border-zinc-800 bg-zinc-50 dark:bg-zinc-900
                    hover:shadow-md transition-all duration-300
                    animation: fadeIn 0.4s ease-out;`}
                  onClick={() => !reorderMode && navigate(`/${artist.slug}`)}
                >
                  <div className="flex items-center gap-3">
                    {artist.albumCovers[0] && (
                      <img
                        src={artist.albumCovers[0]}
                        alt={artist.name}
                        className="w-12 h-12 rounded-md object-cover flex-shrink-0"
                        draggable={false}
                      />
                    )}
                    <div className="flex-1 min-w-0">
                      <p className="font-semibold text-zinc-900 dark:text-white text-sm truncate">
                        {artist.name}
                      </p>
                      <p className="text-zinc-400 dark:text-zinc-500 text-xs">
                        {artist.albums.length} albums · {artist.songCount} songs
                      </p>
                    </div>
                    {reorderMode && (
                      <span className="text-zinc-300 dark:text-zinc-600 flex-shrink-0">⋮⋮</span>
                    )}
                  </div>
                </div>
              ))}
            </div>
          )}
        </section>

        <style>{`
          @keyframes fadeIn {
            from {
              opacity: 0;
              transform: translateY(8px);
            }
            to {
              opacity: 1;
              transform: translateY(0);
            }
          }
        `}</style>
      </div>
    </div>
  )
}

function buildMergedIndexData(artists: Array<LoadedArtistData & { index: IndexData['index'] }>): IndexData {
  const songs: SongMeta[] = []
  const songsById: IndexData['songsById'] = {}
  const index: IndexData['index'] = {}

  for (const { artist, songs: artistSongs, index: artistIndex } of artists) {
    const idMap = new Map<string, string>()

    for (const song of artistSongs) {
      const mergedId = `${artist.slug}:${song.id}`
      idMap.set(String(song.id), mergedId)

      const mergedSong: SongMeta = {
        ...song,
        id: mergedId,
        artistName: artist.name,
        artistSlug: artist.slug,
      }

      songs.push(mergedSong)
      songsById[mergedId] = mergedSong
    }

    for (const [token, postingMap] of Object.entries(artistIndex)) {
      if (!index[token]) index[token] = {}

      for (const [songId, positions] of Object.entries(postingMap)) {
        const mergedId = idMap.get(songId)
        if (!mergedId) continue
        index[token][mergedId] = positions
      }
    }
  }

  return { songs, songsById, index }
}

interface ArtistCardProps {
  artist: ArtistCardData
  index: number
  isDragging: boolean
  isDraggingDisabled?: boolean
  onDragStart: () => void
  onDragEnd: () => void
  onDrop: (targetIndex: number) => void
  onClick: () => void
}

function ArtistCard({ artist, index, isDragging, isDraggingDisabled, onDragStart, onDragEnd, onDrop, onClick }: ArtistCardProps) {
  const [dragOver, setDragOver] = useState(false)
  const [justDropped, setJustDropped] = useState(false)

  return (
    <>
      <style>{`
        @keyframes dropBounce {
          0% { transform: scale(1.08); opacity: 0.7; }
          60% { transform: scale(0.96); }
          100% { transform: scale(1); opacity: 1; }
        }
        .drop-bounce {
          animation: dropBounce 0.6s cubic-bezier(0.68, -0.55, 0.265, 1.55);
        }
      `}</style>
      <button
      draggable={!isDraggingDisabled}
      onDragStart={(e) => {
        if (!isDraggingDisabled) {
          e.dataTransfer!.effectAllowed = 'move'
          onDragStart()
        }
      }}
      onDragEnd={onDragEnd}
      onDragOver={(e) => {
        if (!isDraggingDisabled) {
          e.preventDefault()
          e.dataTransfer!.dropEffect = 'move'
          setDragOver(true)
        }
      }}
      onDragLeave={() => setDragOver(false)}
      onDrop={(e) => {
        if (!isDraggingDisabled) {
          e.preventDefault()
          setDragOver(false)
          setJustDropped(true)
          setTimeout(() => setJustDropped(false), 600)
          onDrop(index)
        }
      }}
      onClick={onClick}
      className={`group text-left w-full bg-zinc-50 dark:bg-zinc-900
                 border rounded-2xl overflow-hidden
                 hover:border-zinc-400 dark:hover:border-zinc-600
                 transition-all duration-500 ${isDraggingDisabled ? 'cursor-pointer' : 'cursor-move'}
                 ${isDragging ? 'opacity-40 scale-95 shadow-none' : ''}
                 ${dragOver && !isDraggingDisabled ? 'border-blue-400 dark:border-blue-500 scale-[1.08] shadow-xl dark:shadow-blue-500/20 -translate-y-1' : justDropped ? 'drop-bounce' : 'border-zinc-200 dark:border-zinc-800'}
                 ${!isDragging && !dragOver && !justDropped ? 'shadow-sm dark:shadow-zinc-900/50' : ''}`}
    >
      {/* Album art mosaic */}
      <div className="grid grid-cols-2 aspect-video w-full overflow-hidden">
        {[0, 1, 2, 3].map(i => (
          artist.albumCovers[i] ? (
            <img
              key={i}
              src={artist.albumCovers[i]}
              alt=""
              className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-300"
              draggable={false}
            />
          ) : (
            <div key={i} className="w-full h-full bg-zinc-200 dark:bg-zinc-800" />
          )
        ))}
      </div>

      {/* Info */}
      <div className="p-4">
        <p className="font-semibold text-zinc-900 dark:text-white text-base">{artist.name}</p>
        <p className="text-zinc-400 dark:text-zinc-500 text-xs mt-0.5">
          {artist.albums.length} albums · {artist.songCount} songs
        </p>
      </div>
      </button>
    </>
  )
}
