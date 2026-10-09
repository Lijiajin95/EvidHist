import type { EvidenceOut } from "../../domain/workbenchContract";
import { relationLabels } from "../messages";

/** Evidence entries side by side per source, preserving disagreement. */
export function EvidenceList({ evidence }: { evidence: EvidenceOut[] }) {
  if (evidence.length === 0) {
    return <p data-testid="evidence-empty">该论断还没有绑定证据。</p>;
  }
  return (
    <ul className="evidence-list" data-testid="evidence-list">
      {evidence.map((entry) => (
        <li key={entry.id} className="evidence-entry">
          <p>
            <strong>{entry.source_title}</strong>（版本「{entry.version_label || "无说明"}」，区间 [
            {entry.start}, {entry.end})）
          </p>
          <blockquote>{entry.quote}</blockquote>
          <p>
            关系：<strong>{relationLabels[entry.relation] ?? entry.relation}</strong>
            {entry.note ? ` · ${entry.note}` : ""}
          </p>
          <p>
            <small>{entry.created_at}</small>
          </p>
        </li>
      ))}
    </ul>
  );
}
