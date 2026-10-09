import { useState } from "react";
import { getClaim } from "../../api/workbench";
import type { PendingQuote } from "../../domain/pendingQuote";
import { useLoad, LoadStateView } from "../../hooks/useLoad";
import { reviewStatusLabels } from "../messages";
import { EvidenceBindForm } from "./EvidenceBindForm";
import { EvidenceList } from "./EvidenceList";

interface ClaimDetailViewProps {
  claimId: string;
  pendingQuote: PendingQuote | null;
  onQuoteConsumed: () => void;
  onBack: () => void;
  onBound?: () => void;
}

/** One claim: statement, review status and its evidence from all sources. */
export function ClaimDetailView({
  claimId,
  pendingQuote,
  onQuoteConsumed,
  onBack,
  onBound,
}: ClaimDetailViewProps) {
  const [reloadToken, setReloadToken] = useState(0);
  const [binding, setBinding] = useState(false);
  const state = useLoad(() => getClaim(claimId), [claimId, reloadToken]);

  const handleBound = () => {
    setReloadToken((token) => token + 1);
    onBound?.();
  };

  return (
    <section aria-labelledby="claim-detail-heading">
      <button type="button" onClick={onBack}>
        返回论断列表
      </button>
      <LoadStateView state={state} />
      {state.status === "ok" ? (
        <>
          <h2 id="claim-detail-heading">{state.data.claim.statement}</h2>
          <p>
            核查状态：{reviewStatusLabels[state.data.claim.review_status] ?? "未知"}。位置匹配与
            人工标注都不代表史实已经证实。
          </p>
          <h3>证据</h3>
          <EvidenceList evidence={state.data.evidence} />
          <button type="button" onClick={() => setBinding((previous) => !previous)}>
            {binding ? "取消绑定" : "新增证据绑定"}
          </button>
          {binding ? (
            <EvidenceBindForm
              claimId={claimId}
              pendingQuote={pendingQuote}
              onQuoteConsumed={onQuoteConsumed}
              onBound={handleBound}
            />
          ) : null}
        </>
      ) : null}
    </section>
  );
}
