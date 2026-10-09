import { useState } from "react";
import { listSources } from "../../api/workbench";
import type { SourceSummary } from "../../domain/workbenchContract";
import { useLoad, LoadStateView } from "../../hooks/useLoad";
import { SourceForm } from "./SourceForm";

/** Material list with search and the add-material entry point. */
export function SourceListView({ onOpen }: { onOpen: (id: string) => void }) {
  const [query, setQuery] = useState("");
  const [adding, setAdding] = useState(false);
  const [reloadToken, setReloadToken] = useState(0);
  const state = useLoad(() => listSources(query), [query, reloadToken]);

  return (
    <section aria-labelledby="sources-heading">
      <h2 id="sources-heading">材料</h2>
      <label htmlFor="source-search">搜索材料</label>
      <input
        id="source-search"
        value={query}
        onChange={(event) => setQuery(event.target.value)}
        autoComplete="off"
      />
      <button type="button" onClick={() => setAdding((previous) => !previous)}>
        {adding ? "取消添加" : "添加材料"}
      </button>
      {adding ? <SourceForm onSaved={() => setReloadToken((token) => token + 1)} /> : null}
      <LoadStateView state={state} />
      {state.status === "ok" ? (
        state.data.length === 0 ? (
          <p data-testid="sources-empty">暂无材料。</p>
        ) : (
          <ul data-testid="source-list">
            {state.data.map((source) => (
              <SourceRow key={source.id} source={source} onOpen={onOpen} />
            ))}
          </ul>
        )
      ) : null}
    </section>
  );
}

function SourceRow({ source, onOpen }: { source: SourceSummary; onOpen: (id: string) => void }) {
  return (
    <li>
      <button type="button" onClick={() => onOpen(source.id)}>
        {source.title}
      </button>
      <span> 版本 {source.version_count}</span>
    </li>
  );
}
