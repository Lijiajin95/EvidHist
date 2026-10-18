import type { Conversation } from "../../domain/chatContract";

export interface ConversationGroup {
  label: string;
  items: Conversation[];
}

const DAY_MS = 24 * 60 * 60 * 1000;

function startOfDay(moment: Date): number {
  return new Date(moment.getFullYear(), moment.getMonth(), moment.getDate()).getTime();
}

/** 相对时间分组（参考 DeepSeek 侧栏）：今天／昨天／7 天内／30 天内／更早。 */
export function groupConversations(
  conversations: Conversation[],
  now: Date = new Date(),
): ConversationGroup[] {
  const today = startOfDay(now);
  const buckets: ConversationGroup[] = [
    { label: "今天", items: [] },
    { label: "昨天", items: [] },
    { label: "7 天内", items: [] },
    { label: "30 天内", items: [] },
    { label: "更早", items: [] },
  ];
  for (const conversation of conversations) {
    const updated = new Date(conversation.updated_at);
    if (Number.isNaN(updated.getTime())) {
      buckets[4]?.items.push(conversation);
      continue;
    }
    const day = startOfDay(updated);
    const age = Math.round((today - day) / DAY_MS);
    const bucket = age <= 0 ? 0 : age === 1 ? 1 : age <= 7 ? 2 : age <= 30 ? 3 : 4;
    buckets[bucket]?.items.push(conversation);
  }
  return buckets.filter((bucket) => bucket.items.length > 0);
}
