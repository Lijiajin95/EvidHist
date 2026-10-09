import { splitByCodePointRange } from "../domain/offsets";

interface QuoteHighlightProps {
  text: string;
  start: number;
  end: number;
}

/** Renders the source text with the located citation range highlighted. */
export function QuoteHighlight({ text, start, end }: QuoteHighlightProps) {
  const segments = splitByCodePointRange(text, start, end);
  return (
    <p className="source-text" data-testid="source-highlight">
      {segments.before}
      <mark data-testid="highlighted-quote">{segments.quote}</mark>
      {segments.after}
    </p>
  );
}
