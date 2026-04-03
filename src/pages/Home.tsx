import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { ThemeToggle } from '../components/ThemeToggle'

interface Artist {
  slug: string
  name: string
  songsPath: string
  indexPath: string
}

interface ArtistCardData extends Artist {
  songCount: number
  albumCovers: string[]   // up to 4 unique album art URLs, for the mosaic
  albums: string[]
}

interface Props {
  theme: 'dark' | 'light'
  onToggleTheme: () => void
}

export default function Home({ theme, onToggleTheme }: Props) {
  const [artists, setArtists] = useState<ArtistCardData[]>([])
  const navigate = useNavigate()

  useEffect(() => {
    fetch('/data/artists.json')
      .then(r => r.json())
      .then(async (list: Artist[]) => {
        const cards = await Promise.all(list.map(async artist => {
          const songs = await fetch(artist.songsPath).then(r => r.json())
          // Unique albums in release order
          const albumMap = new Map<string, string>()
          for (const s of songs) {
            if (!albumMap.has(s.album) && s.albumArt) albumMap.set(s.album, s.albumArt)
          }
          return {
            ...artist,
            songCount: songs.length,
            albums: Array.from(albumMap.keys()),
            albumCovers: Array.from(albumMap.values()).slice(0, 4),
          }
        }))
        setArtists(cards)
      })
  }, [])

  return (
    <div className="min-h-screen bg-white dark:bg-zinc-950 text-zinc-900 dark:text-zinc-100">
      <div className="fixed top-4 right-4">
        <ThemeToggle theme={theme} onToggle={onToggleTheme} />
      </div>
      <div className="max-w-3xl mx-auto px-4 py-16">
        <header className="mb-12">
          <h1 className="text-3xl font-bold tracking-tight text-zinc-900 dark:text-white">
            Liner Labs
          </h1>
          <p className="text-zinc-400 dark:text-zinc-500 mt-1 text-sm">
            Search lyrics across your favourite artists
          </p>
        </header>

        {artists.length === 0 ? (
          <p className="text-zinc-400 text-sm">Loading…</p>
        ) : (
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            {artists.map(artist => (
              <ArtistCard key={artist.slug} artist={artist} onClick={() => navigate(`/${artist.slug}`)} />
            ))}
          </div>
        )}
      </div>
    </div>
  )
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
