"""对话持久化的验收（真实 PostgreSQL）。

对应[对话功能方案](../docs/chat-feature-plan-2026-10-18.md)第 3 节。这里固定的是
状态流转与幂等这些关键路径：标题取值、客户端消息去重、事件序号、未完成消息不得进入
历史上下文、中止幂等。
"""

from __future__ import annotations

import pytest
import pytest_asyncio
from sqlalchemy import delete, select

from evidhist.chat_service import (
    ConversationNotFoundError,
    append_event,
    append_user_message,
    conversation_history,
    create_conversation,
    finish_message,
    get_conversation,
    list_conversations,
    start_assistant_message,
)
from evidhist.db import create_engine, create_session_factory
from evidhist.db_migrations import apply_migrations
from evidhist.models import ConversationRow, MessageEventRow, MessageRow

pytestmark = pytest.mark.integration

pytest_plugins = ["pytest_asyncio"]


@pytest_asyncio.fixture
async def migrated(database_url: str) -> str:
    engine = create_engine(database_url)
    await apply_migrations(engine)
    await engine.dispose()
    return database_url


@pytest_asyncio.fixture
async def store(migrated: str):
    engine = create_engine(migrated)
    factory = create_session_factory(engine)
    async with factory() as session:
        await session.execute(delete(MessageEventRow))
        await session.execute(delete(MessageRow))
        await session.execute(delete(ConversationRow))
        await session.commit()
    yield factory
    await engine.dispose()


async def test_title_comes_from_the_first_user_message(store) -> None:
    async with store() as session:
        conversation = await create_conversation(session)
        assert conversation.title == "新对话"

        await append_user_message(
            session, conversation.id, content="于謙在北京保衛戰中的作用是什麼?"
        )
        await session.commit()

        refreshed = await get_conversation(session, conversation.id)
        assert refreshed.conversation.title == "于謙在北京保衛戰中的作用是什麼?"
        assert refreshed.conversation.updated_at >= refreshed.conversation.created_at


async def test_long_first_message_is_truncated_for_the_title(store) -> None:
    async with store() as session:
        conversation = await create_conversation(session)
        await append_user_message(session, conversation.id, content="謙" * 80)
        await session.commit()

        refreshed = await get_conversation(session, conversation.id)

    assert refreshed.conversation.title == "謙" * 40


async def test_repeated_client_message_id_is_idempotent(store) -> None:
    async with store() as session:
        conversation = await create_conversation(session)
        first = await append_user_message(
            session, conversation.id, content="京師戒嚴", client_message_id="c-1"
        )
        await session.commit()
        again = await append_user_message(
            session, conversation.id, content="京師戒嚴", client_message_id="c-1"
        )
        await session.commit()

        detail = await get_conversation(session, conversation.id)

    assert first.id == again.id
    assert len([m for m in detail.messages if m.role == "user"]) == 1


async def test_events_number_monotonically_and_survive_a_reload(store) -> None:
    async with store() as session:
        conversation = await create_conversation(session)
        await append_user_message(session, conversation.id, content="問題")
        reply = await start_assistant_message(session, conversation.id)
        await append_event(session, reply.id, kind="tool_call", payload={"tool": "search"})
        await append_event(session, reply.id, kind="tool_result", payload={"hits": 3})
        await append_event(session, reply.id, kind="token", payload={"text": "于謙"})
        await session.commit()

        detail = await get_conversation(session, conversation.id)

    events = [
        event
        for message in detail.messages
        if message.role == "assistant"
        for event in message.events
    ]
    assert [event.seq for event in events] == [1, 2, 3]
    assert events[0].payload == {"tool": "search"}
    assert events[1].kind == "tool_result"


async def test_unfinished_assistant_message_stays_out_of_history(store) -> None:
    async with store() as session:
        conversation = await create_conversation(session)
        await append_user_message(session, conversation.id, content="第一問")
        streaming = await start_assistant_message(session, conversation.id)
        await append_event(session, streaming.id, kind="token", payload={"text": "部分"})
        await session.commit()

        pending = await conversation_history(session, conversation.id)
        await finish_message(session, streaming.id, status="done")
        await session.commit()
        completed = await conversation_history(session, conversation.id)

    assert [message.role for message in pending] == ["user"]
    assert [message.role for message in completed] == ["user", "assistant"]


async def test_finish_is_idempotent_and_records_stop_and_failure(store) -> None:
    async with store() as session:
        conversation = await create_conversation(session)
        await append_user_message(session, conversation.id, content="問題")
        stopped = await start_assistant_message(session, conversation.id)
        await finish_message(session, stopped.id, status="stopped", error="user_stop")
        await finish_message(session, stopped.id, status="done")
        await session.commit()
        after_stop = await get_conversation(session, conversation.id)

        failed = await start_assistant_message(session, conversation.id)
        await finish_message(session, failed.id, status="failed", error="tool_budget")
        await session.commit()
        after_failure = await get_conversation(session, conversation.id)

    stopped_row = next(m for m in after_stop.messages if m.id == stopped.id)
    failed_row = next(m for m in after_failure.messages if m.id == failed.id)
    assert (stopped_row.status, stopped_row.error) == ("stopped", "user_stop")
    assert (failed_row.status, failed_row.error) == ("failed", "tool_budget")


async def test_unknown_conversation_is_reported(store) -> None:
    async with store() as session:
        with pytest.raises(ConversationNotFoundError):
            await get_conversation(session, __import__("uuid").uuid4())


async def test_conversations_are_listed_by_recent_activity(store) -> None:
    async with store() as session:
        older = await create_conversation(session)
        newer = await create_conversation(session)
        await append_user_message(session, older.id, content="较早")
        await session.commit()
        await append_user_message(session, newer.id, content="较新")
        await session.commit()

        listed = await list_conversations(session)

    assert [item.id for item in listed] == [newer.id, older.id]


async def test_message_rows_are_deleted_with_their_conversation(store) -> None:
    """级联删除保护：删除会话后消息与事件不残留。"""
    async with store() as session:
        conversation = await create_conversation(session)
        await append_user_message(session, conversation.id, content="問題")
        reply = await start_assistant_message(session, conversation.id)
        await append_event(session, reply.id, kind="token", payload={"text": "x"})
        await session.commit()

        await session.delete(await session.get(ConversationRow, conversation.id))
        await session.commit()

        messages = (await session.execute(select(MessageRow))).scalars().all()
        events = (await session.execute(select(MessageEventRow))).scalars().all()

    assert messages == []
    assert events == []


async def test_a_second_user_message_keeps_the_first_title(store) -> None:
    async with store() as session:
        conversation = await create_conversation(session)
        await append_user_message(session, conversation.id, content="第一个问题")
        await session.commit()
        await append_user_message(session, conversation.id, content="第二个问题")
        await session.commit()

        refreshed = await get_conversation(session, conversation.id)

    assert refreshed.conversation.title == "第一个问题"


async def test_finishing_an_unknown_message_is_reported(store) -> None:
    async with store() as session:
        with pytest.raises(ConversationNotFoundError):
            await finish_message(session, __import__("uuid").uuid4(), status="done")


async def test_finishing_stores_the_final_content(store) -> None:
    async with store() as session:
        conversation = await create_conversation(session)
        await append_user_message(session, conversation.id, content="问题")
        reply = await start_assistant_message(session, conversation.id)
        await finish_message(session, reply.id, status="done", content="最终回答")
        await session.commit()

        detail = await get_conversation(session, conversation.id)

    finished = next(message for message in detail.messages if message.id == reply.id)
    assert finished.content == "最终回答"
