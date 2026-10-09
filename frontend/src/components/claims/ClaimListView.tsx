import { useState } from "react";
import { listClaims } from "../../api/workbench";
import { useLoad, LoadStateView } from "../../hooks/useLoad";
import { reviewStatusLabels } from "../messages";
import { ClaimForm } from "./ClaimForm";

/** Claim list with evidence counts and the create-claim entry point. */
export function ClaimListView({ onOpen }: { onOpen: (id: string) => void }) {
  const [creating, setCreating] = useState(false);
  const [reloadToken, setReloadToken] = useState(0);
  const state = useLoad(() => listClaims(), [reloadToken]);

  return (
    <section aria-labelledby="claims-heading">
      <h2 id="claims-heading">论断</h2>
      <button type="button" onClick={() => setCreating((previous) => !previous)}>
        {creating ? "取消新建" : "新建论断"}
      </button>
      {creating ? <ClaimForm onSaved={() => setReloadToken((token) => token + 1)} /> : null}
      <LoadStateView state={state} />
      {state.status === "ok" ? (
        state.data.length === 0 ? (
          <p data-testid="claims-empty">暂无论断。</p>
        ) : (
          <ul data-testid="claim-list">
            {state.data.map((claim) => (
              <li key={claim.id}>
                <button type="button" onClick={() => onOpen(claim.id)}>
                  {claim.statement}
                </button>
                <span>
                  {" "}
                  {reviewStatusLabels[claim.review_status] ?? claim.review_status} · 证据{" "}
                  {claim.evidence_count}
                </span>
              </li>
            ))}
          </ul>
        )
      ) : null}
    </section>
  );
}
