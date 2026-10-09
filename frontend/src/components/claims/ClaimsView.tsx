import { useState } from "react";
import type { PendingQuote } from "../../domain/pendingQuote";
import { ClaimDetailView } from "./ClaimDetailView";
import { ClaimListView } from "./ClaimListView";

interface ClaimsViewProps {
  pendingQuote: PendingQuote | null;
  onQuoteConsumed: () => void;
}

/** Claims view: the list, or one claim's evidence workbench. */
export function ClaimsView({ pendingQuote, onQuoteConsumed }: ClaimsViewProps) {
  const [openClaimId, setOpenClaimId] = useState<string | null>(null);

  return (
    <section aria-label="论断">
      {pendingQuote !== null ? (
        <div className="pending-quote" data-testid="pending-quote">
          <p>
            待绑定引文（版本「{pendingQuote.versionLabel || "无说明"}」，区间 [{pendingQuote.start},{" "}
            {pendingQuote.end})）：
          </p>
          <blockquote>{pendingQuote.quote}</blockquote>
          <button type="button" onClick={onQuoteConsumed}>
            放弃该引文
          </button>
        </div>
      ) : null}
      {openClaimId !== null ? (
        <ClaimDetailView
          claimId={openClaimId}
          pendingQuote={pendingQuote}
          onQuoteConsumed={onQuoteConsumed}
          onBack={() => setOpenClaimId(null)}
        />
      ) : (
        <ClaimListView onOpen={setOpenClaimId} />
      )}
    </section>
  );
}
