import { Link } from 'react-router-dom'
import { HighlightedLine } from './HighlightedLine'
import { tokenize } from '../lib/tokenize'
import type { SearchResult } from '../types'

const MAX_LINES_SHOWN = 3

interface Props {
  result: SearchResult
  query: string
}

export function ResultCard({ result, query }: Props) {
  const { song, matchedLineIndices, positions } = result
  const queryTokens = tokenize(query)
  const shown = matchedLineIndices.slice(0, MAX_LINES_SHOWN)
  const extra = matchedLineIndices.length - MAX_LINES_SHOWN

  const lineToWordIdx = new Map<number, number>()
  for (const [lineIdx, wordIdx] of positions) {
    if (!lineToWordIdx.has(lineIdx)) lineToWordIdx.set(lineIdx, wordIdx)
  }

  return (
    <div className="bg-zinc-50 dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 rounded-xl p-4 space-y-2">
      <div className="flex items-center gap-3">
        {song.albumArt && (
          <img
            src={song.albumArt}
            alt={song.album}
            className="w-10 h-10 rounded-md object-cover shrink-0 shadow-sm"
          />
        )}
        <div>
          <p className="font-semibold text-zinc-900 dark:text-white text-sm">{song.title}</p>
          <p className="text-zinc-400 dark:text-zinc-500 text-xs mt-0.5 flex flex-wrap items-center gap-1">
            {song.artistName && song.artistSlug && (
              <>
                <Link
                  to={`/${song.artistSlug}`}
                  className="text-zinc-500 dark:text-zinc-400 hover:text-zinc-700 dark:hover:text-zinc-200 transition-colors"
                >
                  {song.artistName}
                </Link>
                <span aria-hidden="true">·</span>
              </>
            )}
            <span>{song.album} · {song.year}</span>
          </p>
        </div>
      </div>

      <div className="space-y-1 pt-1 border-t border-zinc-200 dark:border-zinc-800">
        {shown.map(lineIdx => (
          <p key={lineIdx} className="text-zinc-600 dark:text-zinc-300 text-sm leading-relaxed font-mono">
            <HighlightedLine
              line={song.lines[lineIdx]}
              queryTokens={queryTokens}
              phraseLength={queryTokens.length}
            />
          </p>
        ))}
        {extra > 0 && (
          <p className="text-zinc-400 dark:text-zinc-600 text-xs italic">
            …and {extra} more line{extra !== 1 ? 's' : ''}
          </p>
        )}
      </div>
    </div>
  )
}
