import { isEmptyRange, splitByCodePointRange } from "../domain/offsets";
import type { LocateTaskState } from "../domain/locateTask";
import { QuoteHighlight } from "./QuoteHighlight";

const failureMessages: Record<string, string> = {
  version_mismatch: "版本不符：引文版本与提供的文本版本不同。",
  invalid_range: "区间无效：起止位置必须构成文本内的有效范围。",
  quote_mismatch: "字句不符：该区间的文本与引文不一致。",
  network: "网络失败：无法连接校验服务。",
  invalid_response: "非法响应：服务返回的数据不符合契约。",
};

/** Loading, result, empty-result and failure display for the locate task. */
export function TaskStatus({ state }: { state: LocateTaskState }) {
  if (state.status === "idle") {
    return <p aria-live="polite">尚未提交校验请求。</p>;
  }
  if (state.status === "loading") {
    return (
      <p aria-live="polite" role="status">
        正在校验…
      </p>
    );
  }
  if (state.status === "failed") {
    const message =
      state.reason.kind === "api"
        ? failureMessages[state.reason.code]
        : failureMessages[state.reason.kind];
    return (
      <p role="alert" data-testid="locate-failure">
        {message}
      </p>
    );
  }
  const segments = splitByCodePointRange(
    state.request.source.text,
    state.location.start,
    state.location.end,
  );
  if (isEmptyRange(state.location.start, state.location.end) || segments.quote === "") {
    return (
      <p role="status" data-testid="locate-empty">
        结果为空：返回的区间没有可展示的引文。
      </p>
    );
  }
  return (
    <section aria-live="polite" data-testid="locate-result">
      <p>
        已定位：版本 {state.location.version_id}，区间 [{state.location.start}, {state.location.end}
        )。
      </p>
      <QuoteHighlight
        text={state.request.source.text}
        start={state.location.start}
        end={state.location.end}
      />
      <p className="scope-note">此结果仅说明位置与字句在所提供文本中一致。</p>
    </section>
  );
}
