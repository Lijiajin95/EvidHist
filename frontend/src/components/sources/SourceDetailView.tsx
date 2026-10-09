import { useState } from "react";
import { getSource } from "../../api/workbench";
import type { PendingQuote } from "../../domain/pendingQuote";
import { useLoad, LoadStateView } from "../../hooks/useLoad";
import { VersionContentPanel } from "./VersionContentPanel";
import { VersionForm } from "./VersionForm";
import { VersionList } from "./VersionList";

interface SourceDetailViewProps {
  sourceId: string;
  onBack: () => void;
  onUseQuote: (quote: PendingQuote) => void;
}

/** One material: its metadata, immutable versions and the active version text. */
export function SourceDetailView({ sourceId, onBack, onUseQuote }: SourceDetailViewProps) {
  const [reloadToken, setReloadToken] = useState(0);
  const [openVersionId, setOpenVersionId] = useState<string | null>(null);
  const [adding, setAdding] = useState(false);
  const state = useLoad(() => getSource(sourceId), [sourceId, reloadToken]);

  return (
    <section aria-labelledby="source-detail-heading">
      <button type="button" onClick={onBack}>
        返回材料列表
      </button>
      <LoadStateView state={state} />
      {state.status === "ok" ? (
        <>
          <h2 id="source-detail-heading">{state.data.source.title}</h2>
          <dl>
            <div>
              <dt>来源说明</dt>
              <dd>{state.data.source.origin || "（未填写）"}</dd>
            </div>
            <div>
              <dt>材料使用条件</dt>
              <dd>{state.data.source.usage_terms || "（未填写）"}</dd>
            </div>
          </dl>
          <h3>版本</h3>
          <VersionList
            versions={state.data.versions}
            openVersionId={openVersionId}
            onOpen={setOpenVersionId}
          />
          <button type="button" onClick={() => setAdding((previous) => !previous)}>
            {adding ? "取消新增版本" : "新增版本"}
          </button>
          {adding ? (
            <VersionForm sourceId={sourceId} onSaved={() => setReloadToken((token) => token + 1)} />
          ) : null}
          {openVersionId !== null ? (
            <VersionContentPanel versionId={openVersionId} onUseQuote={onUseQuote} />
          ) : null}
        </>
      ) : null}
    </section>
  );
}
