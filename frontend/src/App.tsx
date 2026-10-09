import { useCallback, useState } from "react";
import { Nav, type View } from "./components/Nav";
import { ToolView } from "./components/ToolView";
import type { PendingQuote } from "./domain/pendingQuote";
import { SourcesView } from "./components/sources/SourcesView";
import { ClaimsView } from "./components/claims/ClaimsView";

/**
 * EvidHist v0.1 史料与引用工作台: materials, claims and the explicit-text
 * locate tool in one shell. Evidence bindings always point at persisted
 * versions; the interface never presents a position match as proof that a
 * historical statement has been verified.
 */
export function App() {
  const [view, setView] = useState<View>("sources");
  const [pendingQuote, setPendingQuote] = useState<PendingQuote | null>(null);

  const handleUseQuote = useCallback((quote: PendingQuote) => {
    setPendingQuote(quote);
    setView("claims");
  }, []);

  const handleQuoteConsumed = useCallback(() => {
    setPendingQuote(null);
  }, []);

  return (
    <main className="app">
      <h1>EvidHist 史料与引用工作台</h1>
      <Nav view={view} onChange={setView} />
      {view === "sources" ? (
        <SourcesView onUseQuote={handleUseQuote} />
      ) : view === "claims" ? (
        <ClaimsView pendingQuote={pendingQuote} onQuoteConsumed={handleQuoteConsumed} />
      ) : (
        <ToolView />
      )}
    </main>
  );
}
