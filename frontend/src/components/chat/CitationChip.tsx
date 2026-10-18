interface CitationView {
  version_id: string;
  start: number;
  end: number;
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
    version_id: entry.version_id,
    start: typeof entry.start === "number" ? entry.start : 0,
    end: typeof entry.end === "number" ? entry.end : 0,
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

function label(citation: CitationView): string {
  const parts = [citation.work, citation.volume].filter(
    (part): part is string => typeof part === "string" && part !== "",
  );
  return parts.length > 0 ? parts.join("·") : citation.version_id.slice(0, 8);
}

/** 引文卡片：逐字引文、出处区间与程序校验结果（只读展示）。 */
export function CitationList({ citations }: { citations: Record<string, unknown>[] }) {
  const views = readCitations(citations);
  if (views.length === 0) {
    return null;
  }
  return (
    <ul className="chat-citations" aria-label="引文校验">
      {views.map((citation, index) => (
        <li
          key={`${citation.version_id}-${String(citation.start)}-${String(index)}`}
          className={`chat-citation${citation.ok ? "" : " failed"}`}
        >
          <span className="chat-citation-quote">{citation.exact_quote}</span>
          <span className="chat-citation-source">
            {label(citation)} {citation.start}-{citation.end}
            {citation.ok ? "· 通过程序校验" : `· ${citation.code ?? "未通过"}`}
          </span>
        </li>
      ))}
    </ul>
  );
}
