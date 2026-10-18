/**
 * Chat API client: REST calls plus the SSE reader for POST /messages.
 *
 * EventSource cannot POST, so the stream is read from `fetch` directly. The
 * parser is a pure function of the byte stream: it buffers until a blank line,
 * parses `event:`/`data:` pairs, and drops payloads that are not JSON objects
 * (a malformed event must never abort the rest of the answer).
 */

import { requestJson, requestJsonWithStatus } from "./client";
import {
  conversationDetailSchema,
  conversationListSchema,
  conversationSchema,
  stopResultSchema,
  type Conversation,
  type ConversationDetail,
  type StreamEvent,
} from "../domain/chatContract";

export interface SseParser {
  push(chunk: string): StreamEvent[];
}

function parseBlock(block: string): StreamEvent | null {
  const lines = block.split(/\r?\n/);
  const kind = lines.find((line) => line.startsWith("event: "))?.slice(7) ?? "";
  const data = lines.find((line) => line.startsWith("data: "))?.slice(6);
  if (kind === "" || data === undefined) {
    return null;
  }
  try {
    const payload: unknown = JSON.parse(data);
    if (typeof payload !== "object" || payload === null || Array.isArray(payload)) {
      return null;
    }
    return { kind, payload: payload as Record<string, unknown> };
  } catch {
    return null;
  }
}

export function createSseParser(): SseParser {
  let buffer = "";
  return {
    push(chunk: string): StreamEvent[] {
      buffer += chunk;
      const events: StreamEvent[] = [];
      let separator = buffer.search(/\r?\n\r?\n/);
      while (separator !== -1) {
        const match = /\r?\n\r?\n/.exec(buffer.slice(separator));
        const block = buffer.slice(0, separator);
        buffer = buffer.slice(separator + (match?.[0].length ?? 2));
        const event = parseBlock(block);
        if (event !== null) {
          events.push(event);
        }
        separator = buffer.search(/\r?\n\r?\n/);
      }
      return events;
    },
  };
}

export async function listConversations(): Promise<Conversation[]> {
  return requestJson("/v1/conversations", conversationListSchema);
}

export async function createConversation(): Promise<Conversation> {
  return requestJsonWithStatus("/v1/conversations", conversationSchema, {
    method: "POST",
    body: {},
  }).then((result) => result.data);
}

export async function getConversation(conversationId: string): Promise<ConversationDetail> {
  return requestJson(`/v1/conversations/${conversationId}`, conversationDetailSchema);
}

export async function stopMessage(messageId: string): Promise<boolean> {
  const result = await requestJson(`/v1/messages/${messageId}/stop`, stopResultSchema, {
    method: "POST",
    body: {},
  });
  return result.stopped;
}

/**
 * 提交一条消息并逐事件回调；`signal` 中止读取（服务端据此把消息收尾为 stopped）。
 */
export async function streamMessage(
  conversationId: string,
  content: string,
  onEvent: (event: StreamEvent) => void,
  options: { clientMessageId?: string; signal?: AbortSignal } = {},
): Promise<void> {
  const init: RequestInit = {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      content,
      client_message_id: options.clientMessageId ?? null,
    }),
  };
  if (options.signal !== undefined) {
    init.signal = options.signal;
  }
  const response = await fetch(`/v1/conversations/${conversationId}/messages`, init);
  if (!response.ok || response.body === null) {
    throw new Error("chat_stream_unavailable");
  }
  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  const parser = createSseParser();
  for (;;) {
    const { done, value } = await reader.read();
    if (done) {
      break;
    }
    for (const event of parser.push(decoder.decode(value, { stream: true }))) {
      onEvent(event);
    }
  }
}
