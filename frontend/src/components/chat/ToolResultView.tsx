import type { ReactNode } from "react";

import { asRecord, type LabelMap } from "./toolLabels";

function text(value: unknown, limit = 120): string {
  const raw = typeof value === "string" ? value : typeof value === "number" ? String(value) : "";
  return raw.length > limit ? `${raw.slice(0, limit)}…` : raw;
}

function label(labels: LabelMap, versionId: unknown): string {
  return typeof versionId === "string" ? (labels.get(versionId) ?? "出处未标注") : "出处未标注";
}

function HitList({ result, labels }: { result: Record<string, unknown>; labels: LabelMap }) {
  const hits = Array.isArray(result.hits) ? result.hits : [];
  return (
    <ul className="chat-tool-list">
      {hits.map((item, index) => {
        const hit = asRecord(item) ?? {};
        return (
          <li key={String(index)}>
            <span className="chat-tool-source">{label(labels, hit.version_id)}</span>
            <span className="chat-tool-quote">{text(hit.quote, 200)}</span>
            <span className="chat-tool-context">{text(hit.context, 120)}</span>
          </li>
        );
      })}
    </ul>
  );
}

function MaterialList({ result }: { result: Record<string, unknown> }) {
  const materials = Array.isArray(result.materials) ? result.materials : [];
  return (
    <ul className="chat-tool-list">
      {materials.map((item, index) => {
        const material = asRecord(item) ?? {};
        const work = text(material.work, 60);
        const volume = text(material.volume, 40);
        return (
          <li key={String(index)}>
            <span className="chat-tool-source">
              {work}
              {volume === "" ? "" : `·${volume}`}
            </span>
            <span className="chat-tool-context">
              {typeof material.chars === "number" ? `${String(material.chars)} 字` : ""}
            </span>
          </li>
        );
      })}
    </ul>
  );
}

function ReadText({ result }: { result: Record<string, unknown> }) {
  return typeof result.text === "string" ? (
    <p className="chat-tool-context">{text(result.text, 200)}</p>
  ) : null;
}

function ExactQuote({ result }: { result: Record<string, unknown> }) {
  return typeof result.exact_quote === "string" ? (
    <p className="chat-tool-quote">{result.exact_quote}</p>
  ) : null;
}

function VerifyOutcome({ result }: { result: Record<string, unknown> }) {
  return (
    <p className="chat-tool-context">
      {result.ok === true ? "通过程序校验" : `未通过：${text(result.code, 40)}`}
    </p>
  );
}

function PaperList({ result }: { result: Record<string, unknown> }) {
  const records = Array.isArray(result.records) ? result.records : [];
  return (
    <ul className="chat-tool-list">
      {records.map((item, index) => {
        const record = asRecord(item) ?? {};
        const meta = [text(record.year, 8), text(record.venue, 60)]
          .filter((part) => part !== "")
          .join(" · ");
        return (
          <li key={String(index)}>
            <span className="chat-tool-source">{text(record.title, 100)}</span>
            <span className="chat-tool-context">{meta}</span>
          </li>
        );
      })}
    </ul>
  );
}

const RENDERERS: Record<
  string,
  (props: { result: Record<string, unknown>; labels: LabelMap }) => ReactNode
> = {
  search: HitList,
  list_materials: MaterialList,
  read: ReadText,
  exact_quote: ExactQuote,
  verify_citation: VerifyOutcome,
  search_papers: PaperList,
};

/** 工具结果的只读呈现：只给材料·卷次、原文与出处标签，不显示编号与码点区间。 */
export function ToolResultView({
  tool,
  result,
  labels,
}: {
  tool: string;
  result: Record<string, unknown>;
  labels: LabelMap;
}) {
  if (result.ok === false) {
    return null;
  }
  const render = RENDERERS[tool];
  return render === undefined ? null : render({ result, labels });
}
