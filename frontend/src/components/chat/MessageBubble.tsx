import Markdown from "react-markdown";
import remarkGfm from "remark-gfm";

import { ToolCallCard } from "./ToolCallCard";
import { CitationList } from "./CitationChip";
import { cleanAnswerText } from "./answerText";
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
  // 旧回答的正文写死了内部编号与码点区间，渲染前隐去并如实告知隐去了几处。
  const answer = author === "user" ? null : cleanAnswerText(content);
  return (
    <article className={`chat-message chat-${author}`} data-status={status}>
      {author === "user" ? (
        <p className="chat-user-text">{content}</p>
      ) : (
        <>
          <AnswerBody text={answer?.text ?? content} hidden={answer?.hidden ?? 0} />
          <ToolCallCard events={events} />
          <CitationList citations={citations.map((event) => event.payload)} />
          <AnswerFooter
            verdict={typeof review?.payload.verdict === "string" ? review.payload.verdict : null}
            status={status}
            error={error}
          />
        </>
      )}
    </article>
  );
}

function AnswerFooter({
  verdict,
  status,
  error,
}: {
  verdict: string | null;
  status: ChatMessage["status"];
  error: string | null;
}) {
  return (
    <>
      {verdict === null ? null : (
        <p className="chat-review" data-verdict={verdict}>
          评审：{verdict}
        </p>
      )}
      {status === "failed" ? (
        <p className="chat-error" role="alert">
          本轮未完成：{error ?? "未知原因"}
        </p>
      ) : null}
      {status === "stopped" ? <p className="chat-stopped">已按请求中止。</p> : null}
    </>
  );
}

function AnswerBody({ text, hidden }: { text: string; hidden: number }) {
  return (
    <>
      <div className="chat-answer">
        <Markdown remarkPlugins={[remarkGfm]}>{text}</Markdown>
      </div>
      {hidden === 0 ? null : (
        <p className="chat-note">已隐藏 {String(hidden)} 处内部编号或码点区间。</p>
      )}
    </>
  );
}

/** 把已落库的消息事件转成展示用事件（与服务端事件同构）。 */
export function storedEvents(message: ChatMessage): StreamEvent[] {
  return message.events.map((event) => ({ kind: event.kind, payload: event.payload }));
}
