import type { StreamEvent } from "../../domain/chatContract";

interface ToolStep {
  tool: string;
  arguments: Record<string, unknown>;
  result: Record<string, unknown> | null;
}

function collectSteps(events: StreamEvent[]): ToolStep[] {
  const steps: ToolStep[] = [];
  for (const event of events) {
    if (event.kind === "tool_call") {
      const tool = typeof event.payload.tool === "string" ? event.payload.tool : "tool";
      const args = event.payload.arguments;
      steps.push({
        tool,
        arguments:
          typeof args === "object" && args !== null ? (args as Record<string, unknown>) : {},
        result: null,
      });
    }
    if (event.kind === "tool_result") {
      const previous = steps.at(-1);
      if (previous !== undefined) {
        const result = event.payload.result;
        previous.result =
          typeof result === "object" && result !== null
            ? (result as Record<string, unknown>)
            : null;
      }
    }
  }
  return steps;
}

function summarize(step: ToolStep): string {
  const result = step.result;
  if (result === null) {
    return "执行中…";
  }
  if (result.ok === false) {
    const code = typeof result.code === "string" ? result.code : "unknown";
    return `未成功：${code}`;
  }
  const hits = result.hits;
  if (Array.isArray(hits)) {
    return `命中 ${hits.length} 处`;
  }
  const records = result.records;
  if (Array.isArray(records)) {
    const errors = Array.isArray(result.errors) ? result.errors.length : 0;
    return `题录 ${records.length} 条${errors > 0 ? `，${errors} 个来源失败` : ""}`;
  }
  if (typeof result.text === "string") {
    return `读取 ${result.text.length} 字`;
  }
  return "已完成";
}

/** 工具调用折叠卡片：默认收起，展开后给出参数与结果摘要。 */
export function ToolCallCard({ events }: { events: StreamEvent[] }) {
  const steps = collectSteps(events);
  if (steps.length === 0) {
    return null;
  }
  return (
    <div className="chat-tools">
      {steps.map((step, index) => (
        <details key={`${step.tool}-${String(index)}`} className="chat-tool">
          <summary>
            {step.tool} · {summarize(step)}
          </summary>
          <p className="chat-tool-args">参数：{JSON.stringify(step.arguments)}</p>
          {step.result === null ? null : (
            <pre className="chat-tool-result">{JSON.stringify(step.result, null, 2)}</pre>
          )}
        </details>
      ))}
    </div>
  );
}
