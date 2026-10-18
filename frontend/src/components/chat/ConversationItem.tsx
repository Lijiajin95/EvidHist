import type { Conversation } from "../../domain/chatContract";

/** 单条会话：只显示标题（超长省略），时间放在 title 提示里。 */
export function ConversationItem({
  conversation,
  active,
  onSelect,
}: {
  conversation: Conversation;
  active: boolean;
  onSelect: (conversationId: string) => void;
}) {
  return (
    <li>
      <button
        type="button"
        className={active ? "active" : undefined}
        aria-current={active ? "true" : undefined}
        title={conversation.title}
        onClick={() => onSelect(conversation.id)}
      >
        {conversation.title}
      </button>
    </li>
  );
}
