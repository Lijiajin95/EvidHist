import { useState } from "react";

import { ConversationItem } from "./ConversationItem";
import { groupConversations } from "./conversationGroups";
import type { Conversation } from "../../domain/chatContract";

function ChatGroups({
  groups,
  activeId,
  onSelect,
}: {
  groups: ReturnType<typeof groupConversations>;
  activeId: string | null;
  onSelect: (conversationId: string) => void;
}) {
  return (
    <nav className="chat-groups" aria-label="历史会话">
      {groups.map((group) => (
        <section key={group.label}>
          <h2>{group.label}</h2>
          <ul>
            {group.items.map((conversation) => (
              <ConversationItem
                key={conversation.id}
                conversation={conversation}
                active={conversation.id === activeId}
                onSelect={onSelect}
              />
            ))}
          </ul>
        </section>
      ))}
      {groups.length === 0 ? <p className="chat-empty">暂无会话</p> : null}
    </nav>
  );
}

/** 左侧会话栏：品牌、新建、按时间分组的会话列表；收起后只留品牌行。 */
export function ConversationList({
  conversations,
  activeId,
  onCreate,
  onSelect,
}: {
  conversations: Conversation[];
  activeId: string | null;
  onCreate: () => void;
  onSelect: (conversationId: string) => void;
}) {
  const [collapsed, setCollapsed] = useState(false);
  const groups = groupConversations(conversations);
  return (
    <aside className="chat-sidebar" aria-label="会话列表">
      <div className="chat-brand">
        <span className="chat-mark" aria-hidden="true" />
        <span className="chat-brand-name">EvidHist</span>
        <button
          type="button"
          className="chat-collapse"
          aria-label={collapsed ? "展开会话" : "收起会话"}
          aria-expanded={!collapsed}
          onClick={() => setCollapsed((value) => !value)}
        >
          <span aria-hidden="true">{collapsed ? "»" : "«"}</span>
        </button>
      </div>
      {collapsed ? null : (
        <>
          <button type="button" className="chat-new" onClick={onCreate}>
            开启新对话
          </button>
          <ChatGroups groups={groups} activeId={activeId} onSelect={onSelect} />
        </>
      )}
    </aside>
  );
}
