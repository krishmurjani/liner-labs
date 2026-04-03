import type { SongMeta } from '../types'

interface AlbumInfo {
  name: string
  year: number
  art?: string
}

interface Props {
  albums: AlbumInfo[]
  selected: Set<string>
  onChange: (selected: Set<string>) => void
}

export function AlbumFilter({ albums, selected, onChange }: Props) {
  const toggle = (name: string) => {
    const next = new Set(selected)
    if (next.has(name)) next.delete(name)
    else next.add(name)
    onChange(next)
  }

  return (
    <div className="flex flex-wrap gap-2">
      {albums.map(album => {
        const active = selected.has(album.name)
        return (
          <button
            key={album.name}
            onClick={() => toggle(album.name)}
            className={`flex items-center gap-2 px-3 py-1.5 rounded-full text-xs
                        border transition-all duration-150 select-none
                        ${active
                          ? 'border-zinc-400 dark:border-zinc-400 bg-zinc-200 dark:bg-zinc-700 text-zinc-900 dark:text-zinc-100'
                          : 'border-zinc-200 dark:border-zinc-700 bg-transparent text-zinc-400 dark:text-zinc-500 hover:border-zinc-400 dark:hover:border-zinc-500 hover:text-zinc-700 dark:hover:text-zinc-300'
                        }`}
          >
            {album.art && (
              <img
                src={album.art}
                alt=""
                className="w-4 h-4 rounded-sm object-cover"
              />
            )}
            <span>{album.name}</span>
          </button>
        )
      })}
    </div>
  )
}

/** Derive sorted unique album list from songs array */
export function albumsFromSongs(songs: SongMeta[]): AlbumInfo[] {
  const seen = new Map<string, AlbumInfo>()
  for (const song of songs) {
    if (!seen.has(song.album)) {
      seen.set(song.album, { name: song.album, year: song.year, art: song.albumArt })
    }
  }
  return Array.from(seen.values()).sort((a, b) => a.year - b.year)
}
