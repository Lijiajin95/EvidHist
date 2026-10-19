interface CitationView {
  exact_quote: string;
  ok: boolean;
  code: string | null;
  work: string | undefined;
  volume: string | undefined;
}

function readCitation(item: unknown): CitationView | null {
  if (typeof item !== "object" || item === null) {
    return null;
  }
  const entry = item as Record<string, unknown>;
  if (typeof entry.version_id !== "string" || typeof entry.exact_quote !== "string") {
    return null;
  }
  return {
    exact_quote: entry.exact_quote,
    ok: entry.ok === true,
    code: typeof entry.code === "string" ? entry.code : null,
    work: typeof entry.work === "string" ? entry.work : undefined,
    volume: typeof entry.volume === "string" ? entry.volume : undefined,
  };
}

function readCitations(payloads: Record<string, unknown>[]): CitationView[] {
  return payloads.flatMap((payload) => {
    const citations = payload.citations;
    if (!Array.isArray(citations)) {
      return [];
    }
    return citations.map(readCitation).filter((view): view is CitationView => view !== null);
  });
}

/** 出处只写材料名与卷次；缺标签时如实说「未标注」，绝不回退到内部编号。 */
export function citationSource(work?: string, volume?: string): string {
  const parts = [work, volume].filter(
    (part): part is string => typeof part === "string" && part.trim() !== "",
  );
  return parts.length > 0 ? parts.join("·") : "出处未标注";
}

/** 引文卡片：原文 + 材料·卷次 + 程序校验结果（不显示内部标识与码点区间）。 */
export function CitationList({ citations }: { citations: Record<string, unknown>[] }) {
  const views = readCitations(citations);
  if (views.length === 0) {
    return null;
  }
  return (
    <ul className="chat-citations" aria-label="引文校验">
      {views.map((citation, index) => (
        <li
          key={`${citation.exact_quote}-${String(index)}`}
          className={`chat-citation${citation.ok ? "" : " failed"}`}
        >
          <span className="chat-citation-quote">{citation.exact_quote}</span>
          <span className="chat-citation-source">
            {citationSource(citation.work, citation.volume)}
            {citation.ok ? " · 通过程序校验" : ` · ${citation.code ?? "未通过"}`}
          </span>
        </li>
      ))}
    </ul>
  );
}
