import { ToolResultView } from "./ToolResultView";
import { asRecord, collectLabels, type LabelMap } from "./toolLabels";
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
      const args = asRecord(event.payload.arguments) ?? {};
      steps.push({ tool, arguments: args, result: null });
    }
    if (event.kind === "tool_result") {
      const previous = steps.at(-1);
      if (previous !== undefined) {
        previous.result = asRecord(event.payload.result);
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
    return `命中 ${String(hits.length)} 处`;
  }
  const records = result.records;
  if (Array.isArray(records)) {
    const errors = Array.isArray(result.errors) ? result.errors.length : 0;
    return `题录 ${String(records.length)} 条${errors > 0 ? `，${String(errors)} 个来源失败` : ""}`;
  }
  if (typeof result.text === "string") {
    return `读取 ${String(result.text.length)} 字`;
  }
  return "已完成";
}

/** 参数只呈现看得懂的部分：检索词、原文，或已知版本的「材料·卷次」。 */
function describeArguments(step: ToolStep, labels: LabelMap): string {
  const query = step.arguments.query;
  if (typeof query === "string" && query !== "") {
    return `检索词：${query}`;
  }
  const quote = step.arguments.exact_quote;
  if (typeof quote === "string" && quote !== "") {
    return `原文：${quote}`;
  }
  const versionId = step.arguments.version_id;
  if (typeof versionId === "string") {
    return labels.get(versionId) ?? "";
  }
  return "";
}

/** 工具调用折叠卡片：默认收起，展开后给出可读参数与结果（隐藏编号与码点区间）。 */
export function ToolCallCard({ events }: { events: StreamEvent[] }) {
  const steps = collectSteps(events);
  if (steps.length === 0) {
    return null;
  }
  const labels = collectLabels(events);
  return (
    <div className="chat-tools">
      {steps.map((step, index) => {
        const args = describeArguments(step, labels);
        return (
          <details key={`${step.tool}-${String(index)}`} className="chat-tool">
            <summary>
              {step.tool} · {summarize(step)}
            </summary>
            {args === "" ? null : <p className="chat-tool-args">{args}</p>}
            {step.result === null ? null : (
              <ToolResultView tool={step.tool} result={step.result} labels={labels} />
            )}
          </details>
        );
      })}
    </div>
  );
}
