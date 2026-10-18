import { useCallback, useRef, useState, type ReactNode } from "react";

import { ConversationList } from "./ConversationList";
import { MessageBubble, storedEvents } from "./MessageBubble";
import {
  createConversation,
  getConversation,
  listConversations,
  stopMessage,
  streamMessage,
} from "../../api/chat";
import { LoadStateView, useLoad, type LoadState } from "../../hooks/useLoad";
import type { ChatMessage, Conversation, StreamEvent } from "../../domain/chatContract";

interface LiveTurn {
  answer: string;
  events: StreamEvent[];
}

const NOOP = (): undefined => undefined;

/** 会话列表：用共享加载 hook 读取，新建后重新拉取。 */
function useConversations() {
  const [reloadToken, setReloadToken] = useState(0);
  const [activeId, setActiveId] = useState<string | null>(null);
  const state = useLoad(() => listConversations(), [reloadToken]);

  const create = useCallback(async () => {
    const conversation = await createConversation();
    setActiveId(conversation.id);
    setReloadToken((token) => token + 1);
  }, []);

  return {
    conversations: state.status === "ok" ? state.data : [],
    state,
    activeId,
    setActiveId,
    create,
  };
}

/** 选中会话的消息；切换会话或一轮结束后重新读取。 */
function useMessages(activeId: string | null, reloadToken: number) {
  const state = useLoad(
    () => (activeId === null ? Promise.resolve(null) : getConversation(activeId)),
    [activeId, reloadToken],
  );
  const messages: ChatMessage[] =
    state.status === "ok" && state.data !== null ? state.data.messages : [];
  return { messages, state };
}

/** 一轮生成：订阅 SSE、累积事件、记录错误与中止。 */
function useTurn(activeId: string | null, onSettled: () => void) {
  const [live, setLive] = useState<LiveTurn | null>(null);
  const [error, setError] = useState<string | null>(null);
  const abortRef = useRef<AbortController | null>(null);
  const messageIdRef = useRef<string | null>(null);
  const lastSentRef = useRef<string>("");

  const send = useCallback(
    async (content: string): Promise<void> => {
      if (activeId === null || content.trim() === "" || live !== null) {
        return;
      }
      lastSentRef.current = content;
      messageIdRef.current = null;
      setError(null);
      setLive({ answer: "", events: [] });
      const controller = new AbortController();
      abortRef.current = controller;
      try {
        await streamMessage(
          activeId,
          content,
          (event) => {
            if (event.kind === "message_start" && typeof event.payload.message_id === "string") {
              messageIdRef.current = event.payload.message_id;
            }
            setLive((current) => (current === null ? current : applyStreamEvent(current, event)));
          },
          { signal: controller.signal },
        );
      } catch {
        setError(
          controller.signal.aborted ? "已中止本轮生成。" : "本轮生成失败，可重试发送同一条消息。",
        );
      } finally {
        abortRef.current = null;
        setLive(null);
        onSettled();
      }
    },
    [activeId, live, onSettled],
  );

  // 先请服务端收尾（状态 stopped），再断开本地连接；否则消息会停在 streaming。
  const stop = useCallback(() => {
    const messageId = messageIdRef.current;
    if (messageId !== null) {
      stopMessage(messageId).catch(NOOP);
    }
    abortRef.current?.abort();
  }, []);

  return { live, error, lastSentRef, send, stop };
}

function ChatThread({
  messages,
  live,
  error,
  loading,
  onRetry,
}: {
  messages: ChatMessage[];
  live: LiveTurn | null;
  error: string | null;
  loading: boolean;
  onRetry: () => void;
}) {
  return (
    <section className="chat-thread" aria-label="对话内容">
      {loading ? <p role="status">正在加载…</p> : null}
      {messages.map((message) => (
        <MessageBubble
          key={message.id}
          author={message.role}
          content={message.content}
          events={storedEvents(message)}
          status={message.status}
          error={message.error}
        />
      ))}
      {live === null ? null : (
        <MessageBubble
          author="assistant"
          content={live.answer}
          events={live.events}
          status="streaming"
          error={null}
        />
      )}
      {error === null ? null : (
        <p className="chat-error" role="alert">
          {error}
          <button type="button" onClick={onRetry}>
            重试
          </button>
        </p>
      )}
    </section>
  );
}

/** 空态：问候语与输入区同组居中（参考 DeepSeek 首页）。 */
function ChatHero({ composer }: { composer: ReactNode }) {
  return (
    <div className="chat-hero">
      <p className="chat-greeting">
        <span className="chat-mark" aria-hidden="true" />
        你好，让我们开始聊天吧
      </p>
      <p className="chat-hero-hint">检索已入库史料、逐字校验引文、生成报告并请求评审。</p>
      <div className="chat-hero-composer">{composer}</div>
    </div>
  );
}

function ComposerActions({
  streaming,
  canSend,
  onStop,
}: {
  streaming: boolean;
  canSend: boolean;
  onStop: () => void;
}) {
  return (
    <div className="chat-composer-row">
      <span className="chat-composer-hint">Enter 发送 · Shift + Enter 换行</span>
      {streaming ? (
        <button type="button" className="chat-round" aria-label="中止" onClick={onStop}>
          <span aria-hidden="true">■</span>
        </button>
      ) : (
        <button type="submit" className="chat-round" aria-label="发送" disabled={!canSend}>
          <span aria-hidden="true">↑</span>
        </button>
      )}
    </div>
  );
}

function ChatComposer({
  draft,
  onDraft,
  onSubmit,
  streaming,
  onStop,
  canSend,
}: {
  draft: string;
  onDraft: (value: string) => void;
  onSubmit: () => void;
  streaming: boolean;
  onStop: () => void;
  canSend: boolean;
}) {
  return (
    <form
      className="chat-composer"
      onSubmit={(event) => {
        event.preventDefault();
        onSubmit();
      }}
    >
      <textarea
        aria-label="输入消息"
        rows={2}
        value={draft}
        placeholder="给 EvidHist 发送消息"
        onChange={(event) => onDraft(event.target.value)}
        onKeyDown={(event) => {
          if (event.key === "Enter" && !event.shiftKey) {
            event.preventDefault();
            onSubmit();
          }
        }}
      />
      <ComposerActions streaming={streaming} canSend={canSend} onStop={onStop} />
    </form>
  );
}

interface ChatMainProps {
  empty: boolean;
  messages: ChatMessage[];
  live: LiveTurn | null;
  error: string | null;
  loading: boolean;
  composer: ReactNode;
  onRetry: () => void;
  listState: LoadState<Conversation[]>;
}

/** 主区：空态问候（含输入区）或消息流；输入区在有消息时固定底部。 */
function ChatMain(props: ChatMainProps) {
  return (
    <div className="chat-main">
      {props.empty ? (
        <ChatHero composer={props.composer} />
      ) : (
        <ChatThread
          messages={props.messages}
          live={props.live}
          error={props.error}
          loading={props.loading}
          onRetry={props.onRetry}
        />
      )}
      <LoadStateView state={props.listState} />
      {props.empty ? null : <div className="chat-composer-area">{props.composer}</div>}
    </div>
  );
}

/** 对话视图：左侧会话栏、中间消息流、底部输入区（DeepSeek 网页版式）。 */
export function ChatView() {
  const { conversations, state, activeId, setActiveId, create } = useConversations();
  const [messageToken, setMessageToken] = useState(0);
  const { messages, state: messageState } = useMessages(activeId, messageToken);
  const settle = useCallback(() => setMessageToken((token) => token + 1), []);
  const { live, error, lastSentRef, send, stop } = useTurn(activeId, settle);
  const [draft, setDraft] = useState("");

  const submit = (): void => {
    const content = draft;
    setDraft("");
    send(content).catch(NOOP);
  };

  // 空态才显示问候语；有错误时必须露出错误与重试入口。
  const empty =
    messages.length === 0 && live === null && error === null && messageState.status !== "loading";

  return (
    <div className="chat-shell">
      <ConversationList
        conversations={conversations}
        activeId={activeId}
        onCreate={() => {
          create().catch(NOOP);
        }}
        onSelect={setActiveId}
      />
      <ChatMain
        empty={empty}
        messages={messages}
        live={live}
        error={error}
        loading={messageState.status === "loading"}
        composer={
          <ChatComposer
            draft={draft}
            onDraft={setDraft}
            onSubmit={submit}
            streaming={live !== null}
            onStop={stop}
            canSend={activeId !== null && draft.trim() !== ""}
          />
        }
        onRetry={() => {
          send(lastSentRef.current).catch(NOOP);
        }}
        listState={state}
      />
    </div>
  );
}

/** 流式事件叠加：token 累积正文，其余事件按序保留。 */
function applyStreamEvent(turn: LiveTurn, event: StreamEvent): LiveTurn {
  const answer =
    event.kind === "token" && typeof event.payload.text === "string"
      ? turn.answer + event.payload.text
      : turn.answer;
  return { answer, events: [...turn.events, event] };
}
