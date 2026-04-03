/**
 * Normalize a string into an array of tokens (individual words).
 *
 * Rules — must stay IDENTICAL to the tokenize() function in scripts/build_index.py.
 * If you change one, change the other, then rebuild the index.
 *
 *   1. Lowercase everything
 *   2. Remove apostrophes entirely  →  "can't" → "cant", "i'm" → "im"
 *   3. Replace non-alphanumeric chars with spaces  →  hyphens, commas, etc. become word breaks
 *   4. Split on whitespace, drop empty strings
 *
 * Why remove apostrophes instead of splitting on them?
 *   Splitting "can't" → ["can", "t"] makes "t" a useless junk token.
 *   Removing the apostrophe keeps "cant" as one token that matches what
 *   users actually type when searching.
 *
 * Why no stop-word removal?
 *   Stop words ("the", "a", "in") are needed for phrase search.
 *   Searching "in the end" would break if "the" was removed from the index.
 */
export function tokenize(text: string): string[] {
  return text
    .toLowerCase()
    .replace(/'/g, '')             // remove apostrophes
    .replace(/[^a-z0-9\s]/g, ' ') // other punctuation → space
    .split(/\s+/)
    .filter(Boolean)
}
