/** A citation selected in a version's text, waiting to be bound as evidence. */
export interface PendingQuote {
  versionId: string;
  versionLabel: string;
  start: number;
  end: number;
  quote: string;
}
