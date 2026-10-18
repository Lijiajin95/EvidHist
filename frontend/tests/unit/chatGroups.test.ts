import { describe, expect, it } from "vitest";

import { groupConversations } from "../../src/components/chat/conversationGroups";

const NOW = new Date("2026-10-19T12:00:00+08:00");

function conversation(title: string, updatedAt: string) {
  return {
    id: `00000000-0000-4000-8000-${title.padEnd(12, "0").slice(0, 12)}`,
    title,
    created_at: updatedAt,
    updated_at: updatedAt,
  };
}

describe("groupConversations", () => {
  it("groups by relative age, newest first inside each group", () => {
    const groups = groupConversations(
      [
        conversation("今天早上", "2026-10-19T09:00:00+08:00"),
        conversation("昨天", "2026-10-18T20:00:00+08:00"),
        conversation("三天前", "2026-10-16T10:00:00+08:00"),
        conversation("二十天前", "2026-09-29T10:00:00+08:00"),
        conversation("很久以前", "2026-07-01T10:00:00+08:00"),
      ],
      NOW,
    );

    expect(groups.map((group) => group.label)).toEqual([
      "今天",
      "昨天",
      "7 天内",
      "30 天内",
      "更早",
    ]);
    expect(groups[0]?.items.map((item) => item.title)).toEqual(["今天早上"]);
    expect(groups[2]?.items.map((item) => item.title)).toEqual(["三天前"]);
  });

  it("keeps the incoming order inside a group and drops empty groups", () => {
    const groups = groupConversations(
      [
        conversation("较新", "2026-10-19T11:00:00+08:00"),
        conversation("较早", "2026-10-19T08:00:00+08:00"),
      ],
      NOW,
    );

    expect(groups).toHaveLength(1);
    expect(groups[0]?.items.map((item) => item.title)).toEqual(["较新", "较早"]);
  });

  it("returns no groups for an empty list", () => {
    expect(groupConversations([], NOW)).toEqual([]);
  });

  it("treats a boundary just past midnight as yesterday", () => {
    const groups = groupConversations([conversation("午夜", "2026-10-18T23:59:00+08:00")], NOW);

    expect(groups[0]?.label).toBe("昨天");
  });
});
