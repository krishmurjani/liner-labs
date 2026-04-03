interface Props {
  line: string
  queryTokens: string[]
  phraseLength: number
}

export function HighlightedLine({ line, queryTokens, phraseLength }: Props) {
  type TokenSpan = { token: string; start: number; end: number }
  const spans: TokenSpan[] = []

  let i = 0
  while (i < line.length) {
    if (!/[a-zA-Z0-9']/.test(line[i])) { i++; continue }
    const start = i
    while (i < line.length && /[a-zA-Z0-9']/.test(line[i])) i++
    const rawWord = line.slice(start, i)
    const normalized = rawWord.toLowerCase().replace(/'/g, '')
    if (normalized) spans.push({ token: normalized, start, end: i })
  }

  const matchStart = queryTokens.length > 0
    ? spans.findIndex((_, si) => queryTokens.every((qt, qi) => spans[si + qi]?.token === qt))
    : -1
  const matchEnd = matchStart >= 0 ? matchStart + phraseLength : -1

  const parts: React.ReactNode[] = []
  let cursor = 0

  spans.forEach(({ start, end }, si) => {
    if (cursor < start) parts.push(line.slice(cursor, start))
    const isHighlighted = si >= matchStart && si < matchEnd && matchStart >= 0
    const word = line.slice(start, end)
    parts.push(
      isHighlighted ? (
        <mark key={si} className="bg-yellow-200 dark:bg-yellow-400/30 text-yellow-800 dark:text-yellow-200 rounded px-0.5">
          {word}
        </mark>
      ) : word
    )
    cursor = end
  })

  if (cursor < line.length) parts.push(line.slice(cursor))
  return <span>{parts}</span>
}
