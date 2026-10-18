-- 对话功能（2026-10-18 方案第 3 节）：会话、消息与其结构化事件。
-- 事件保存工具调用、引文校验、评审与运行产物等可复核记录，供刷新后重建界面。
CREATE TABLE conversations (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    title text NOT NULL DEFAULT '新对话',
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE messages (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    conversation_id uuid NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
    role text NOT NULL,
    content text NOT NULL DEFAULT '',
    status text NOT NULL DEFAULT 'done',
    error text,
    client_message_id text,
    created_at timestamptz NOT NULL DEFAULT now(),
    CONSTRAINT messages_role_check CHECK (role IN ('user', 'assistant', 'system')),
    CONSTRAINT messages_status_check CHECK (status IN ('streaming', 'done', 'failed', 'stopped')),
    -- 同一会话内同一客户端消息标识只落一条，重复提交不新建
    CONSTRAINT messages_client_id_unique UNIQUE (conversation_id, client_message_id)
);

CREATE TABLE message_events (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    message_id uuid NOT NULL REFERENCES messages(id) ON DELETE CASCADE,
    seq integer NOT NULL,
    kind text NOT NULL,
    payload jsonb NOT NULL DEFAULT '{}'::jsonb,
    created_at timestamptz NOT NULL DEFAULT now(),
    CONSTRAINT message_events_seq_unique UNIQUE (message_id, seq)
);

CREATE INDEX conversations_updated_at_idx ON conversations (updated_at DESC);
CREATE INDEX messages_conversation_idx ON messages (conversation_id, created_at);
CREATE INDEX message_events_message_idx ON message_events (message_id, seq);
