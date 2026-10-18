"""会话与消息的持久化（对话功能方案第 3 节）。

状态流转与幂等是这里的关键路径：标题取自首条用户消息；同一 `client_message_id`
重复提交只落一条；助手消息先以 `streaming` 落库，结束后才进入历史上下文；结束
状态幂等（已结束的消息不会被后来的调用改写）。事件按 `seq` 单调递增，供界面刷新
后重建工具卡片。
"""

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from evidhist.models import ConversationRow, MessageEventRow, MessageRow, utc_now
from evidhist.store_errors import NotFoundError

DEFAULT_TITLE = "新对话"
TITLE_LIMIT = 40
FINISHED_STATUSES = ("done", "failed", "stopped")


class ConversationNotFoundError(NotFoundError):
    """会话不存在；API 层按 404 处理。"""

    def __init__(self, identifier: str) -> None:
        super().__init__("conversation", identifier)


@dataclass(frozen=True)
class Conversation:
    id: UUID
    title: str
    created_at: datetime
    updated_at: datetime


@dataclass(frozen=True)
class MessageEvent:
    id: UUID
    seq: int
    kind: str
    payload: dict[str, object]
    created_at: datetime


@dataclass(frozen=True)
class Message:
    id: UUID
    conversation_id: UUID
    role: str
    content: str
    status: str
    error: str | None
    created_at: datetime
    events: tuple[MessageEvent, ...] = ()


@dataclass(frozen=True)
class ConversationDetail:
    conversation: Conversation
    messages: tuple[Message, ...]


def _conversation(row: ConversationRow) -> Conversation:
    return Conversation(
        id=row.id, title=row.title, created_at=row.created_at, updated_at=row.updated_at
    )


def _event(row: MessageEventRow) -> MessageEvent:
    return MessageEvent(
        id=row.id, seq=row.seq, kind=row.kind, payload=row.payload, created_at=row.created_at
    )


def _message(row: MessageRow, events: tuple[MessageEvent, ...] = ()) -> Message:
    return Message(
        id=row.id,
        conversation_id=row.conversation_id,
        role=row.role,
        content=row.content,
        status=row.status,
        error=row.error,
        created_at=row.created_at,
        events=events,
    )


async def _require_conversation(session: AsyncSession, conversation_id: UUID) -> ConversationRow:
    row = await session.get(ConversationRow, conversation_id)
    if row is None:
        raise ConversationNotFoundError(str(conversation_id))
    return row


async def create_conversation(session: AsyncSession, *, title: str = DEFAULT_TITLE) -> Conversation:
    row = ConversationRow(title=title)
    session.add(row)
    await session.flush()
    return _conversation(row)


async def append_user_message(
    session: AsyncSession,
    conversation_id: UUID,
    *,
    content: str,
    client_message_id: str | None = None,
) -> Message:
    """写入用户消息；同一 client_message_id 重复提交返回既有行。"""
    conversation = await _require_conversation(session, conversation_id)
    if client_message_id is not None:
        existing = (
            await session.execute(
                select(MessageRow).where(
                    MessageRow.conversation_id == conversation_id,
                    MessageRow.client_message_id == client_message_id,
                )
            )
        ).scalar_one_or_none()
        if existing is not None:
            return _message(existing)

    row = MessageRow(
        conversation_id=conversation_id,
        role="user",
        content=content,
        status="done",
        client_message_id=client_message_id,
    )
    session.add(row)
    if conversation.title == DEFAULT_TITLE and content.strip():
        conversation.title = content.strip()[:TITLE_LIMIT]
    conversation.updated_at = utc_now()
    await session.flush()
    return _message(row)


async def start_assistant_message(session: AsyncSession, conversation_id: UUID) -> Message:
    """开始一条助手回复；内容在流式过程中逐步补全。"""
    conversation = await _require_conversation(session, conversation_id)
    row = MessageRow(conversation_id=conversation_id, role="assistant", status="streaming")
    session.add(row)
    conversation.updated_at = utc_now()
    await session.flush()
    return _message(row)


async def append_event(
    session: AsyncSession, message_id: UUID, *, kind: str, payload: dict[str, object]
) -> MessageEvent:
    """追加结构化事件；seq 从 1 开始，在一条消息内单调递增。"""
    current = (
        await session.execute(
            select(func.max(MessageEventRow.seq)).where(MessageEventRow.message_id == message_id)
        )
    ).scalar_one_or_none()
    row = MessageEventRow(
        message_id=message_id, seq=int(current or 0) + 1, kind=kind, payload=payload
    )
    session.add(row)
    await session.flush()
    return _event(row)


async def finish_message(
    session: AsyncSession,
    message_id: UUID,
    *,
    status: str,
    content: str | None = None,
    error: str | None = None,
) -> Message:
    """结束一条助手消息；已结束的消息保持不变（幂等）。"""
    row = await session.get(MessageRow, message_id)
    if row is None:
        raise ConversationNotFoundError(str(message_id))
    if row.status not in FINISHED_STATUSES:
        row.status = status
        row.error = error
        if content is not None:
            row.content = content
        conversation = await session.get(ConversationRow, row.conversation_id)
        if conversation is not None:  # pragma: no cover - 外键保证会话存在
            conversation.updated_at = utc_now()
    await session.flush()
    return _message(row)


async def get_conversation(session: AsyncSession, conversation_id: UUID) -> ConversationDetail:
    """会话详情：消息按时间、事件按 seq 返回，供界面刷新后重建。"""
    conversation = await _require_conversation(session, conversation_id)
    message_rows = (
        (
            await session.execute(
                select(MessageRow)
                .where(MessageRow.conversation_id == conversation_id)
                .order_by(MessageRow.created_at, MessageRow.id)
            )
        )
        .scalars()
        .all()
    )
    event_rows = (
        (
            await session.execute(
                select(MessageEventRow)
                .where(MessageEventRow.message_id.in_([row.id for row in message_rows]))
                .order_by(MessageEventRow.seq)
            )
        )
        .scalars()
        .all()
    )
    by_message: dict[UUID, list[MessageEvent]] = {}
    for row in event_rows:
        by_message.setdefault(row.message_id, []).append(_event(row))
    return ConversationDetail(
        conversation=_conversation(conversation),
        messages=tuple(_message(row, tuple(by_message.get(row.id, ()))) for row in message_rows),
    )


async def list_conversations(session: AsyncSession, *, limit: int = 50) -> tuple[Conversation, ...]:
    rows = (
        (
            await session.execute(
                select(ConversationRow)
                .order_by(ConversationRow.updated_at.desc(), ConversationRow.created_at.desc())
                .limit(limit)
            )
        )
        .scalars()
        .all()
    )
    return tuple(_conversation(row) for row in rows)


async def conversation_history(session: AsyncSession, conversation_id: UUID) -> tuple[Message, ...]:
    """已完成的消息，按时间顺序；未完成的助手回复不进上下文。"""
    rows = (
        (
            await session.execute(
                select(MessageRow)
                .where(
                    MessageRow.conversation_id == conversation_id,
                    MessageRow.status == "done",
                )
                .order_by(MessageRow.created_at, MessageRow.id)
            )
        )
        .scalars()
        .all()
    )
    return tuple(_message(row) for row in rows)
