import { citationSource } from "./CitationChip";
import type { StreamEvent } from "../../domain/chatContract";

/** 版本编号 → 「材料·卷次」；界面只认标签，不显示内部编号。 */
export type LabelMap = Map<string, string>;

function addRows(labels: LabelMap, rows: unknown): void {
  for (const item of asArray(rows)) {
    const row = asRecord(item);
    if (row === null || typeof row.version_id !== "string") {
      continue;
    }
    labels.set(row.version_id, citationSource(asText(row.work), asText(row.volume)));
  }
}

export function collectLabels(events: StreamEvent[]): LabelMap {
  const labels: LabelMap = new Map();
  for (const event of events) {
    const payload = asRecord(event.payload);
    if (payload === null) {
      continue;
    }
    for (const source of [asRecord(payload.result), payload]) {
      if (source === null) {
        continue;
      }
      addRows(labels, source.hits);
      addRows(labels, source.materials);
      addRows(labels, source.citations);
    }
  }
  return labels;
}

export function asRecord(value: unknown): Record<string, unknown> | null {
  return typeof value === "object" && value !== null ? (value as Record<string, unknown>) : null;
}

function asArray(value: unknown): unknown[] {
  return Array.isArray(value) ? value : [];
}

function asText(value: unknown): string | undefined {
  return typeof value === "string" ? value : undefined;
}
