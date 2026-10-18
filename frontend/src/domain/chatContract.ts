/**
 * Runtime contract for the chat endpoints, mirroring contracts/openapi.json.
 * SSE events carry a `kind` plus a free-form payload: the UI renders the kinds
 * it knows and ignores the rest, so a new backend event never breaks the page.
 */

import { z } from "zod";

const id = z.uuid();
const timestamp = z.iso.datetime({ offset: true });

export const conversationSchema = z.object({
  id,
  title: z.string(),
  created_at: timestamp,
  updated_at: timestamp,
});

export const conversationListSchema = z.array(conversationSchema);

export const chatEventSchema = z.object({
  seq: z.int(),
  kind: z.string(),
  payload: z.record(z.string(), z.unknown()),
});

export const messageSchema = z.object({
  id,
  role: z.enum(["user", "assistant", "system"]),
  content: z.string(),
  status: z.enum(["streaming", "done", "failed", "stopped"]),
  error: z.string().nullable(),
  created_at: timestamp,
  events: z.array(chatEventSchema),
});

export const conversationDetailSchema = z.object({
  conversation: conversationSchema,
  messages: z.array(messageSchema),
});

export const stopResultSchema = z.object({
  message_id: id,
  stopped: z.boolean(),
});

export type Conversation = z.infer<typeof conversationSchema>;
export type ChatMessage = z.infer<typeof messageSchema>;
export type ConversationDetail = z.infer<typeof conversationDetailSchema>;

/** 流式事件：kind + 载荷，未知 kind 由界面安全忽略。 */
export interface StreamEvent {
  kind: string;
  payload: Record<string, unknown>;
}
