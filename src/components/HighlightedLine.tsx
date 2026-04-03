interface Props {
  line: string
  queryTokens: string[]
  phraseLength: number // number of consecutive tokens to highlight
}

/**
 * Renders a lyrics line with the matched word(s) highlighted.
 *
 * Strategy: re-tokenize the line to find word boundaries, then walk the
 * original line character by character to produce spans. This correctly
 * handles apostrophes, punctuation, and any gap between the normalized
 * token and the raw display character.
 *
 * Example:
 *   line: "I didn't know I was broken"
 *   queryTokens: ["didnt"]
 *   → "I " + <mark>didn't</mark> + " know I was broken"
 */
export function HighlightedLine({ line, queryTokens, phraseLength }: Props) {
  // Build a list of {token, charStart, charEnd} from the original line
  type TokenSpan = { token: string; start: number; end: number }
  const spans: TokenSpan[] = []

  let i = 0
  while (i < line.length) {
    // Skip non-word characters
    if (!/[a-zA-Z0-9']/.test(line[i])) {
      i++
      continue
    }
    // Collect a word (letters, digits, apostrophes)
    const start = i
    while (i < line.length && /[a-zA-Z0-9']/.test(line[i])) i++
    const rawWord = line.slice(start, i)
    // Normalize the same way the tokenizer does
    const normalized = rawWord.toLowerCase().replace(/'/g, '')
    if (normalized) spans.push({ token: normalized, start, end: i })
  }

  // Find the first span index where queryTokens (consecutive) start
  const matchStart = queryTokens.length > 0
    ? spans.findIndex((_, si) =>
        queryTokens.every(
          (qt, qi) => spans[si + qi]?.token === qt
        )
      )
    : -1

  const matchEnd = matchStart >= 0 ? matchStart + phraseLength : -1

  // Build the output by walking the original line character by character
  const parts: React.ReactNode[] = []
  let cursor = 0

  spans.forEach(({ start, end }, si) => {
    // Text between previous token end and this token start
    if (cursor < start) parts.push(line.slice(cursor, start))
    const isHighlighted = si >= matchStart && si < matchEnd && matchStart >= 0
    const word = line.slice(start, end)
    parts.push(
      isHighlighted ? (
        <mark key={si} className="bg-yellow-400/30 text-yellow-200 rounded px-0.5">
          {word}
        </mark>
      ) : (
        word
      )
    )
    cursor = end
  })

  // Any trailing characters after the last token
  if (cursor < line.length) parts.push(line.slice(cursor))

  return <span>{parts}</span>
}
