import { describe, expect, it } from "vitest";

import { createSseParser } from "../../src/api/chat";
import { chatEventSchema, conversationSchema, messageSchema } from "../../src/domain/chatContract";

describe("createSseParser", () => {
  it("parses one complete event", () => {
    const parser = createSseParser();

    const events = parser.push('event: token\ndata: {"text":"于謙"}\n\n');

    expect(events).toEqual([{ kind: "token", payload: { text: "于謙" } }]);
  });

  it("keeps a partial event until the terminating blank line arrives", () => {
    const parser = createSseParser();

    expect(parser.push('event: tool_call\ndata: {"tool":"sea')).toEqual([]);
    const events = parser.push('rch"}\n\n');

    expect(events).toEqual([{ kind: "tool_call", payload: { tool: "search" } }]);
  });

  it("parses several events from one chunk and ignores unknown kinds safely", () => {
    const parser = createSseParser();

    const events = parser.push(
      'event: token\ndata: {"text":"a"}\n\nevent: future_thing\ndata: {"x":1}\n\n' +
        'event: token\ndata: {"text":"b"}\n\n',
    );

    expect(events.map((event) => event.kind)).toEqual(["token", "future_thing", "token"]);
    expect(events.at(1)?.payload).toEqual({ x: 1 });
  });

  it("drops events whose data is not a JSON object", () => {
    const parser = createSseParser();

    expect(parser.push("event: token\ndata: not-json\n\n")).toEqual([]);
    expect(parser.push("event: token\ndata: [1,2]\n\n")).toEqual([]);
  });

  it("drops blocks without an event line", () => {
    const parser = createSseParser();

    expect(parser.push('data: {"text":"x"}\n\n')).toEqual([]);
  });

  it("handles CRLF separators used by some proxies", () => {
    const parser = createSseParser();

    expect(parser.push('event: token\r\ndata: {"text":"x"}\r\n\r\n')).toEqual([
      { kind: "token", payload: { text: "x" } },
    ]);
  });
});

describe("chat contracts", () => {
  it("accepts a conversation payload", () => {
    const parsed = conversationSchema.parse({
      id: "3cf22914-9798-49f6-bb28-1bc602077153",
      title: "新对话",
      created_at: "2026-10-18T15:01:34.082174+08:00",
      updated_at: "2026-10-18T15:02:00.000000+08:00",
    });

    expect(parsed.title).toBe("新对话");
  });

  it("accepts messages with events and rejects a missing role", () => {
    const message = {
      id: "3cf22914-9798-49f6-bb28-1bc602077153",
      role: "assistant",
      content: "结论",
      status: "done",
      error: null,
      created_at: "2026-10-18T15:01:34.082174+08:00",
      events: [{ seq: 1, kind: "token", payload: { text: "a" } }],
    };

    expect(messageSchema.parse(message).events).toHaveLength(1);
    expect(messageSchema.safeParse({ ...message, role: undefined }).success).toBe(false);
  });

  it("keeps unknown event kinds but requires seq and kind", () => {
    expect(chatEventSchema.parse({ seq: 2, kind: "future", payload: {} }).kind).toBe("future");
    expect(chatEventSchema.safeParse({ kind: "token", payload: {} }).success).toBe(false);
  });
});
