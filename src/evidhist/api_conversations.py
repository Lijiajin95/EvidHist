"""对话功能的 HTTP 接口（对话功能方案第 4 节）：会话 CRUD、SSE 消息流与中止。

流式采用 `text/event-stream`：每个事件先落库（`message_events`，供刷新后重建），
再推给客户端；助手消息在开始时落库为 `streaming`，结束时写状态与完整回答。
中止是幂等的：记录一次中止请求后，生成器在下一个事件处收尾为 `stopped`。
"""

from __future__ import annotations

import asyncio
import json
import os
from collections.abc import AsyncGenerator, Sequence
from datetime import datetime
from pathlib import Path
from typing import cast
from uuid import UUID

import httpx2
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from evidhist.chat_service import (
    DEFAULT_TITLE,
    MessageEvent,
    append_event,
    append_user_message,
    conversation_history,
    create_conversation,
    finish_message,
    get_conversation,
    list_conversations,
    start_assistant_message,
)
from evidhist.models import MessageRow, SourceRow, TextVersionRow
from evidhist.research.chat import ChatEvent, ChatRequest, Toolbox, stream_reply
from evidhist.research.chat_tools import SessionToolbox
from evidhist.research.executor import ExecutorError, RunLimitExceeded, RunLimits
from evidhist.research.pi_rpc import PiConfig
from evidhist.research.review import PiReviewer, Reviewer
from evidhist.research.tools import Material, ReadOnlyTools
from evidhist.store_errors import NotFoundError

router = APIRouter(prefix="/v1")

CHAT_WALL_SECONDS = 300
CHAT_IDLE_SECONDS = 60
CHAT_TOOL_CALLS = 24
MESSAGE_LIMIT = 4000
_STOP_REQUESTED: set[UUID] = set()


class ConversationCreateIn(BaseModel):
    model_config = ConfigDict(strict=True, extra="forbid")

    title: str = Field(default=DEFAULT_TITLE, min_length=1, max_length=100)


class MessageIn(BaseModel):
    model_config = ConfigDict(strict=True, extra="forbid")

    content: str = Field(min_length=1, max_length=MESSAGE_LIMIT)
    client_message_id: str | None = Field(default=None, max_length=100)


class ConversationOut(BaseModel):
    id: UUID
    title: str
    created_at: datetime
    updated_at: datetime


class EventOut(BaseModel):
    seq: int
    kind: str
    payload: dict[str, object]


class MessageOut(BaseModel):
    id: UUID
    role: str
    content: str
    status: str
    error: str | None
    created_at: datetime
    events: list[EventOut]


class ConversationDetailOut(BaseModel):
    conversation: ConversationOut
    messages: list[MessageOut]


class StopOut(BaseModel):
    message_id: UUID
    stopped: bool


def sse_event(kind: str, payload: dict[str, object]) -> str:
    """一条 SSE 事件；JSON 单行，避免客户端把多行 data 拼错。"""
    body = json.dumps(payload, ensure_ascii=False)
    return f"event: {kind}\ndata: {body}\n\n"


def stored_payload(kind: str, payload: dict[str, object]) -> dict[str, object]:
    """落库前去掉重复载荷：完整回答已写入消息内容，事件里只留计数与用量。"""
    if kind != "message_end":
        return payload
    return {key: value for key, value in payload.items() if key != "answer"}


def pi_config_from_env() -> PiConfig:
    """PI 配置来自环境变量；默认值与本地研究入口保持一致。"""
    home = Path(os.environ.get("EVIDHIST_PI_HOME", str(Path.home() / ".cache" / "pi-home")))
    bin_dir = os.environ.get("EVIDHIST_PI_BIN_DIR", str(Path.home() / ".pi" / "agent" / "bin"))
    return PiConfig(
        provider=os.environ.get("EVIDHIST_PI_PROVIDER", "cc-switch-open-code-go"),
        model=os.environ.get("EVIDHIST_PI_MODEL", "deepseek-v4.1-flash"),
        home=home,
        session_dir=home / "sessions",
        workdir=Path(os.environ.get("EVIDHIST_PI_WORKDIR", str(home))),
        command=os.environ.get("EVIDHIST_PI_COMMAND", "pi"),
        bin_dir=Path(bin_dir),
        thinking=os.environ.get("EVIDHIST_PI_THINKING", "minimal"),
    )


def chat_limits_from_env() -> RunLimits:
    return RunLimits(
        wall_seconds=int(os.environ.get("EVIDHIST_CHAT_WALL_SECONDS", CHAT_WALL_SECONDS)),
        tool_calls=CHAT_TOOL_CALLS,
        idle_seconds=CHAT_IDLE_SECONDS,
    )


def reviewer_from_env(config: PiConfig) -> Reviewer | None:
    """默认委托评审；设 EVIDHIST_CHAT_REVIEW=0 可关闭（少一次模型调用）。"""
    if os.environ.get("EVIDHIST_CHAT_REVIEW", "1") == "0":
        return None
    return PiReviewer(config)


async def load_materials(
    session: AsyncSession, *, works: Sequence[str] = ()
) -> tuple[Material, ...]:
    """材料快照：已入库的来源与版本，按作品与版本标签排序。"""
    statement = (
        select(SourceRow.title, TextVersionRow)
        .join(TextVersionRow, TextVersionRow.source_id == SourceRow.id)
        .order_by(SourceRow.title, TextVersionRow.label)
    )
    if works:
        statement = statement.where(SourceRow.title.in_(works))
    rows = (await session.execute(statement)).all()
    return tuple(
        Material(
            version_id=str(version.id),
            work=title,
            volume=version.label.split("|")[0],
            text=version.content,
        )
        for title, version in rows
    )


def _conversation_out(row: object) -> ConversationOut:
    return ConversationOut.model_validate(row, from_attributes=True)


@router.post("/conversations", response_model=ConversationOut, status_code=201)
async def post_conversation(request: Request, payload: ConversationCreateIn) -> ConversationOut:
    async with request.app.state.session_factory() as session:
        conversation = await create_conversation(session, title=payload.title)
        await session.commit()
    return _conversation_out(conversation)


@router.get("/conversations", response_model=list[ConversationOut])
async def get_conversations(request: Request, limit: int = 50) -> list[ConversationOut]:
    async with request.app.state.session_factory() as session:
        return [_conversation_out(row) for row in await list_conversations(session, limit=limit)]


async def _version_labels(session: AsyncSession) -> dict[str, tuple[str, str]]:
    """版本编号 → （材料名, 卷次）；只取标签列，不读正文。"""
    rows = (
        await session.execute(
            select(SourceRow.title, TextVersionRow.id, TextVersionRow.label).join(
                TextVersionRow, TextVersionRow.source_id == SourceRow.id
            )
        )
    ).all()
    return {str(version_id): (title, label.split("|")[0]) for title, version_id, label in rows}


def _labelled_payload(
    payload: dict[str, object], labels: dict[str, tuple[str, str]]
) -> dict[str, object]:
    """旧消息的引文载荷可能没有作品与卷次，读取时补齐（界面只显示材料·卷次）。"""
    raw = payload.get("citations")
    if not isinstance(raw, list):
        return payload
    enriched: list[object] = []
    for item in cast("list[object]", raw):
        if not isinstance(item, dict):
            enriched.append(item)
            continue
        row = cast("dict[str, object]", item)
        work, volume = labels.get(str(row.get("version_id")), ("", ""))
        enriched.append(
            {
                **row,
                "work": row.get("work") or work,
                "volume": row.get("volume") or volume,
            }
        )
    return {**payload, "citations": enriched}


def _event_out(event: MessageEvent, labels: dict[str, tuple[str, str]]) -> EventOut:
    payload = (
        _labelled_payload(event.payload, labels)
        if event.kind == "citation_check"
        else event.payload
    )
    return EventOut(seq=event.seq, kind=event.kind, payload=payload)


@router.get("/conversations/{conversation_id}", response_model=ConversationDetailOut)
async def get_conversation_detail(request: Request, conversation_id: UUID) -> ConversationDetailOut:
    async with request.app.state.session_factory() as session:
        try:
            detail = await get_conversation(session, conversation_id)
        except NotFoundError:
            raise HTTPException(
                status_code=404, detail={"code": "conversation_not_found"}
            ) from None
        labels = await _version_labels(session)
    return ConversationDetailOut(
        conversation=_conversation_out(detail.conversation),
        messages=[
            MessageOut(
                id=message.id,
                role=message.role,
                content=message.content,
                status=message.status,
                error=message.error,
                created_at=message.created_at,
                events=[_event_out(event, labels) for event in message.events],
            )
            for message in detail.messages
        ],
    )


async def _open_turn(
    factory: async_sessionmaker[AsyncSession], conversation_id: UUID, payload: MessageIn
) -> tuple[UUID, list[dict[str, str]], tuple[Material, ...]]:
    """落库用户消息与新的助手消息，并取回对话历史与材料快照。"""
    async with factory() as session:
        try:
            await append_user_message(
                session,
                conversation_id,
                content=payload.content,
                client_message_id=payload.client_message_id,
            )
            assistant = await start_assistant_message(session, conversation_id)
            history = [
                {"role": message.role, "content": message.content}
                for message in await conversation_history(session, conversation_id)
                if message.role in ("user", "assistant")
            ]
            materials = await load_materials(session)
            await session.commit()
        except NotFoundError:
            raise HTTPException(
                status_code=404, detail={"code": "conversation_not_found"}
            ) from None
    return assistant.id, history, materials


async def _publish(session: AsyncSession, message_id: UUID, event: ChatEvent) -> str:
    """事件先落库（供刷新后重建），再转成 SSE 文本推给客户端。"""
    await append_event(
        session,
        message_id,
        kind=event.kind,
        payload=stored_payload(event.kind, event.payload),
    )
    await session.commit()
    return sse_event(event.kind, event.payload)


async def _pump(
    session: AsyncSession,
    message_id: UUID,
    config: PiConfig,
    chat_request: ChatRequest,
    limits: RunLimits,
) -> AsyncGenerator[str]:
    """把一轮对话的事件逐条落库并转成 SSE；结束、失败与中止都写回消息状态。"""
    answer = ""
    try:
        async for event in stream_reply(config, chat_request, limits):
            if event.kind == "message_end":
                answer = str(event.payload.get("answer", ""))
            yield await _publish(session, message_id, event)
            if message_id in _STOP_REQUESTED:
                await finish_message(session, message_id, status="stopped", content=answer)
                await session.commit()
                yield sse_event("message_end", {"message_id": str(message_id), "status": "stopped"})
                return
        await finish_message(session, message_id, status="done", content=answer)
        await session.commit()
    except (RunLimitExceeded, ExecutorError) as error:
        await finish_message(
            session, message_id, status="failed", content=answer, error=str(error.reason)
        )
        await session.commit()
        yield sse_event("error", {"code": str(error.reason), "message_id": str(message_id)})
    except asyncio.CancelledError:
        # 客户端断开连接：不留下永远 streaming 的消息，按中止收尾后继续抛出。
        await finish_message(session, message_id, status="stopped", content=answer)
        await session.commit()
        raise
    finally:
        _STOP_REQUESTED.discard(message_id)


async def _event_stream(
    factory: async_sessionmaker[AsyncSession],
    *,
    message_id: UUID,
    payload: MessageIn,
    history: list[dict[str, str]],
    materials: tuple[Material, ...],
) -> AsyncGenerator[str]:
    yield sse_event("message_start", {"message_id": str(message_id)})
    async with factory() as session:
        toolbox: Toolbox = SessionToolbox(
            session,
            materials=materials,
            tools=ReadOnlyTools(materials),
            client=httpx2.AsyncClient(),
        )
        config = pi_config_from_env()
        chat_request = ChatRequest(
            question=payload.content,
            materials=materials,
            toolbox=toolbox,
            history=tuple(history),
            reviewer=reviewer_from_env(config),
            run_id=str(message_id),
        )
        async for chunk in _pump(session, message_id, config, chat_request, chat_limits_from_env()):
            yield chunk


@router.post("/conversations/{conversation_id}/messages")
async def post_message(
    request: Request, conversation_id: UUID, payload: MessageIn
) -> StreamingResponse:
    """提交用户消息并以 SSE 流式返回这一轮助手回复。"""
    factory = request.app.state.session_factory
    message_id, history, materials = await _open_turn(factory, conversation_id, payload)
    return StreamingResponse(
        _event_stream(
            factory,
            message_id=message_id,
            payload=payload,
            history=history,
            materials=materials,
        ),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-store", "X-Accel-Buffering": "no"},
    )


@router.post("/messages/{message_id}/stop", response_model=StopOut)
async def stop_message(request: Request, message_id: UUID) -> StopOut:
    """登记一次中止请求；收尾（状态与回答）由 SSE 生成器完成，重复请求幂等。

    已经结束的消息不再中止，返回 `stopped=false`，不谎报停止成功。
    """
    async with request.app.state.session_factory() as session:
        row = await session.get(MessageRow, message_id)
    if row is None:
        raise HTTPException(status_code=404, detail={"code": "message_not_found"})
    if row.status != "streaming":
        return StopOut(message_id=message_id, stopped=False)
    _STOP_REQUESTED.add(message_id)
    return StopOut(message_id=message_id, stopped=True)
