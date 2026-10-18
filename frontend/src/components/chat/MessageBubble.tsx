import Markdown from "react-markdown";
import remarkGfm from "remark-gfm";

import { ToolCallCard } from "./ToolCallCard";
import { CitationList } from "./CitationChip";
import type { ChatMessage, StreamEvent } from "../../domain/chatContract";

/** 助手消息：Markdown 正文 + 工具卡片 + 引文列表（可点击跳转到材料）。 */
export function MessageBubble({
  author,
  content,
  events,
  status,
  error,
}: {
  author: ChatMessage["role"];
  content: string;
  events: StreamEvent[];
  status: ChatMessage["status"];
  error: string | null;
}) {
  const citations = events.filter((event) => event.kind === "citation_check");
  const review = events.find((event) => event.kind === "review");
  return (
    <article className={`chat-message chat-${author}`} data-status={status}>
      {author === "user" ? (
        <p className="chat-user-text">{content}</p>
      ) : (
        <>
          <div className="chat-answer">
            <Markdown remarkPlugins={[remarkGfm]}>{content}</Markdown>
          </div>
          <ToolCallCard events={events} />
          <CitationList citations={citations.map((event) => event.payload)} />
          {review === undefined ? null : (
            <p className="chat-review" data-verdict={String(review.payload.verdict)}>
              评审：{String(review.payload.verdict)}
            </p>
          )}
          {status === "failed" ? (
            <p className="chat-error" role="alert">
              本轮未完成：{error ?? "未知原因"}
            </p>
          ) : null}
          {status === "stopped" ? <p className="chat-stopped">已按请求中止。</p> : null}
        </>
      )}
    </article>
  );
}

/** 把已落库的消息事件转成展示用事件（与服务端事件同构）。 */
export function storedEvents(message: ChatMessage): StreamEvent[] {
  return message.events.map((event) => ({ kind: event.kind, payload: event.payload }));
}
