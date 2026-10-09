/**
 * Code-point ↔ UTF-16 index mapping for citation offsets.
 *
 * The backend counts citation offsets in Unicode code points with an exclusive
 * end, while JavaScript strings and DOM ranges index UTF-16 code units. These
 * helpers are the single place where that conversion happens, so highlighting
 * stays correct for supplementary-plane characters (for example 𠀀, U+20000).
 */

export interface HighlightSegments {
  before: string;
  quote: string;
  after: string;
}

export function codePointLength(text: string): number {
  let count = 0;
  for (const _codePoint of text) {
    count += 1;
  }
  return count;
}

export function utf16IndexFromCodePoint(text: string, codePointIndex: number): number {
  let seen = 0;
  let utf16Index = 0;
  for (const codePoint of text) {
    if (seen === codePointIndex) {
      return utf16Index;
    }
    seen += 1;
    utf16Index += codePoint.length;
  }
  return utf16Index;
}

/** Split text around the half-open [start, end) code-point range of the citation. */
export function splitByCodePointRange(text: string, start: number, end: number): HighlightSegments {
  const beforeEnd = utf16IndexFromCodePoint(text, start);
  const quoteEnd = utf16IndexFromCodePoint(text, end);
  return {
    before: text.slice(0, beforeEnd),
    quote: text.slice(beforeEnd, quoteEnd),
    after: text.slice(quoteEnd),
  };
}

/** True when the range would highlight nothing (for example an empty result). */
export function isEmptyRange(start: number, end: number): boolean {
  return start >= end;
}
