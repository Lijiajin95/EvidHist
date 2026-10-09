import { useState } from "react";
import type { PendingQuote } from "../../domain/pendingQuote";
import { SourceDetailView } from "./SourceDetailView";
import { SourceListView } from "./SourceListView";

/** Materials view: the list, or one source's detail with its versions. */
export function SourcesView({ onUseQuote }: { onUseQuote: (quote: PendingQuote) => void }) {
  const [openSourceId, setOpenSourceId] = useState<string | null>(null);

  if (openSourceId !== null) {
    return (
      <SourceDetailView
        sourceId={openSourceId}
        onBack={() => setOpenSourceId(null)}
        onUseQuote={onUseQuote}
      />
    );
  }
  return <SourceListView onOpen={setOpenSourceId} />;
}
