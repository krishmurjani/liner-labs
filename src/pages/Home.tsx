import { useEffect, useState } from 'react'
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
  const navigate = useNavigate()
  const { results, totalCount, status } = useSearch(megaIndexData, megaQuery, null)

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

        setArtists(cards)

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
          <div className="space-y-1">
            <h2 className="text-sm font-semibold text-zinc-900 dark:text-white">Browse Artists</h2>
            <p className="text-zinc-400 dark:text-zinc-500 text-sm">
              Jump into a single artist catalog.
            </p>
          </div>

          {artists.length === 0 ? (
            <p className="text-zinc-400 text-sm">Loading…</p>
          ) : (
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              {artists.map(artist => (
                <ArtistCard key={artist.slug} artist={artist} onClick={() => navigate(`/${artist.slug}`)} />
              ))}
            </div>
          )}
        </section>
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

function ArtistCard({ artist, onClick }: { artist: ArtistCardData; onClick: () => void }) {
  return (
    <button
      onClick={onClick}
      className="group text-left w-full bg-zinc-50 dark:bg-zinc-900
                 border border-zinc-200 dark:border-zinc-800
                 rounded-2xl overflow-hidden
                 hover:border-zinc-400 dark:hover:border-zinc-600
                 transition-all duration-200"
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
  )
}
