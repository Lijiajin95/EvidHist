import { useState } from "react";
import { getVersion } from "../../api/workbench";
import type { PendingQuote } from "../../domain/pendingQuote";
import { useLoad, LoadStateView } from "../../hooks/useLoad";
import { SelectedQuotePanel, type TextSelection } from "./SelectedQuotePanel";
import { VersionTextArea } from "./VersionTextArea";

interface VersionContentPanelProps {
  versionId: string;
  onUseQuote: (quote: PendingQuote) => void;
}

/**
 * The full text of one immutable version. Selecting text offers verify-then-
 * bind; binding always references the persisted version by ID.
 */
export function VersionContentPanel({ versionId, onUseQuote }: VersionContentPanelProps) {
  const state = useLoad(() => getVersion(versionId), [versionId]);
  const [selection, setSelection] = useState<TextSelection | null>(null);

  const handleBind = () => {
    if (selection === null || state.status !== "ok") {
      return;
    }
    onUseQuote({
      versionId,
      versionLabel: state.data.label,
      start: selection.start,
      end: selection.end,
      quote: selection.quote,
    });
  };

  return (
    <section aria-label="版本全文">
      <LoadStateView state={state} />
      {state.status === "ok" ? (
        <>
          <h4>版本全文（{state.data.label || "无说明"}）</h4>
          <p>在下方文本中选取引文，区间按 Unicode 码点换算；选取的引文仍需绑定到论断才成为证据。</p>
          <VersionTextArea content={state.data.content} onSelection={setSelection} />
          {selection !== null ? (
            <SelectedQuotePanel
              key={`${selection.start}-${selection.end}-${selection.quote}`}
              versionId={versionId}
              selection={selection}
              onBind={handleBind}
            />
          ) : null}
        </>
      ) : null}
    </section>
  );
}
