import { LocateCallError } from "../domain/locateTask";

const codeMessages: Record<string, string> = {
  source_not_found: "材料不存在或已被删除。",
  version_not_found: "文本版本不存在或已被删除。",
  claim_not_found: "论断不存在或已被删除。",
  invalid_range: "区间无效：起止位置必须是文本内的有效范围。",
  quote_mismatch: "字句不符：该区间的文本与引文不一致。",
};

/** Readable Chinese message for any workbench failure; never raw JSON. */
export function workbenchFailureMessage(error: unknown): string {
  if (error instanceof LocateCallError) {
    if (error.failure.kind === "api") {
      return codeMessages[error.failure.code] ?? `操作失败：${error.failure.code}。`;
    }
    if (error.failure.kind === "network") {
      return "无法连接服务。";
    }
    return "非法响应：服务返回的数据不符合契约。";
  }
  return "无法连接服务。";
}

export const relationLabels: Record<string, string> = {
  supports: "支持",
  contradicts: "反对",
  mentions: "提及",
  insufficient: "证据不足",
};

export const reviewStatusLabels: Record<string, string> = {
  unverified: "未核查",
};
