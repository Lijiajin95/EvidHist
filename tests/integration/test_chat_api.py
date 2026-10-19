"""对话 HTTP 接口的验收（真实 PostgreSQL + 假 PI 子进程）。

对应[对话功能方案](../docs/chat-feature-plan-2026-10-18.md)第 4 节：会话 CRUD、SSE 事件
顺序与落库、刷新后可重建事件、中止与失败状态。
"""

from __future__ import annotations

import json
import stat
from pathlib import Path

import pytest
import pytest_asyncio
from fastapi.testclient import TestClient
from pydantic import SecretStr
from sqlalchemy import delete

from evidhist.api import create_app
from evidhist.db import create_engine, create_session_factory
from evidhist.db_migrations import apply_migrations
from evidhist.models import (
    ClaimRow,
    ConversationRow,
    EvidenceRow,
    MessageEventRow,
    MessageRow,
    SourceRow,
    TextVersionRow,
)
from evidhist.settings import Settings

pytestmark = pytest.mark.integration

pytest_plugins = ["pytest_asyncio"]

REPO = Path(__file__).resolve().parents[2]
FAKE_PI = REPO / "tests" / "fixtures" / "fake_pi.py"


def parse_sse(body: str) -> list[tuple[str, dict]]:
    """把 SSE 文本还原成 (事件名, 载荷) 序列。"""
    events: list[tuple[str, dict]] = []
    for block in body.strip().split("\n\n"):
        lines = [line for line in block.splitlines() if line]
        kind = next((line[7:] for line in lines if line.startswith("event: ")), "")
        data = next((line[6:] for line in lines if line.startswith("data: ")), "{}")
        events.append((kind, json.loads(data)))
    return events


@pytest_asyncio.fixture
async def chat_client(database_url: str, tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("FAKE_PI_MODE", "ok")
    monkeypatch.setenv("EVIDHIST_PI_COMMAND", str(FAKE_PI))
    (tmp_path / "pi-home").mkdir(parents=True, exist_ok=True)
    monkeypatch.setenv("EVIDHIST_PI_HOME", str(tmp_path / "pi-home"))
    monkeypatch.setenv("EVIDHIST_PI_WORKDIR", str(tmp_path))
    monkeypatch.setenv("EVIDHIST_CHAT_REVIEW", "1")
    FAKE_PI.chmod(FAKE_PI.stat().st_mode | stat.S_IXUSR)

    engine = create_engine(database_url)
    await apply_migrations(engine)
    factory = create_session_factory(engine)
    async with factory() as session:
        for table in (
            MessageEventRow,
            MessageRow,
            ConversationRow,
            EvidenceRow,
            ClaimRow,
            TextVersionRow,
            SourceRow,
        ):
            await session.execute(delete(table))
        await session.commit()
    application = create_app(
        settings=Settings(database_url=SecretStr(database_url)), session_factory=factory
    )
    with TestClient(application) as client:
        client.app.state.test_factory = factory  # type: ignore[attr-defined]
        yield client
    await engine.dispose()


def create(client: TestClient) -> str:
    response = client.post("/v1/conversations", json={})
    assert response.status_code == 201, response.text
    return str(response.json()["id"])


def test_conversation_crud_lists_and_returns_events(chat_client: TestClient) -> None:
    conversation_id = create(chat_client)

    listed = chat_client.get("/v1/conversations")
    assert listed.status_code == 200
    assert [item["id"] for item in listed.json()] == [conversation_id]

    streamed = chat_client.post(
        f"/v1/conversations/{conversation_id}/messages",
        json={"content": "于謙在守禦中的作用?", "client_message_id": "c-1"},
    )
    assert streamed.status_code == 200
    assert streamed.headers["content-type"].startswith("text/event-stream")

    events = parse_sse(streamed.text)
    kinds = [kind for kind, _payload in events]
    assert kinds[0] == "message_start"
    assert "tool_call" in kinds
    assert "token" in kinds
    assert "citation_check" in kinds
    assert kinds[-1] == "message_end"

    detail = chat_client.get(f"/v1/conversations/{conversation_id}")
    body = detail.json()
    assert body["conversation"]["title"] == "于謙在守禦中的作用?"
    roles = [message["role"] for message in body["messages"]]
    assert roles == ["user", "assistant"]
    assistant = body["messages"][1]
    assert assistant["status"] == "done"
    assert assistant["content"].startswith("## 结论")
    stored_kinds = [event["kind"] for event in assistant["events"]]
    assert stored_kinds == kinds[1:]
    assert all("answer" not in event["payload"] for event in assistant["events"])


def test_repeating_a_client_message_id_does_not_create_a_second_turn(
    chat_client: TestClient,
) -> None:
    conversation_id = create(chat_client)
    payload = {"content": "京師戒嚴", "client_message_id": "c-9"}
    chat_client.post(f"/v1/conversations/{conversation_id}/messages", json=payload)
    chat_client.post(f"/v1/conversations/{conversation_id}/messages", json=payload)

    body = chat_client.get(f"/v1/conversations/{conversation_id}").json()
    user_messages = [item for item in body["messages"] if item["role"] == "user"]

    assert len(user_messages) == 1


def test_stopping_a_finished_message_reports_not_stopped(chat_client: TestClient) -> None:
    conversation_id = create(chat_client)
    chat_client.post(f"/v1/conversations/{conversation_id}/messages", json={"content": "问题"})
    body = chat_client.get(f"/v1/conversations/{conversation_id}").json()
    assistant_id = next(item["id"] for item in body["messages"] if item["role"] == "assistant")

    stopped = chat_client.post(f"/v1/messages/{assistant_id}/stop")

    assert stopped.status_code == 200
    assert stopped.json() == {"message_id": assistant_id, "stopped": False}


def test_unknown_conversation_and_message_are_404(chat_client: TestClient) -> None:
    missing = "00000000-0000-0000-0000-000000000000"

    assert chat_client.get(f"/v1/conversations/{missing}").status_code == 404
    assert (
        chat_client.post(
            f"/v1/conversations/{missing}/messages", json={"content": "问题"}
        ).status_code
        == 404
    )
    assert chat_client.post(f"/v1/messages/{missing}/stop").status_code == 404


def test_a_failed_pi_run_is_recorded_as_failed(
    chat_client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("FAKE_PI_MODE", "unsettled")
    monkeypatch.setenv("EVIDHIST_CHAT_WALL_SECONDS", "5")
    conversation_id = create(chat_client)

    streamed = chat_client.post(
        f"/v1/conversations/{conversation_id}/messages", json={"content": "问题"}
    )

    events = parse_sse(streamed.text)
    assert events[-1][0] == "error"
    assert events[-1][1]["code"] == "timeout"
    body = chat_client.get(f"/v1/conversations/{conversation_id}").json()
    assistant = next(item for item in body["messages"] if item["role"] == "assistant")
    assert assistant["status"] == "failed"
    assert assistant["error"] == "timeout"


async def _seed_old_citation(database_url: str) -> str:
    """造一条「旧格式」消息：引文载荷只有编号与区间，没有作品与卷次。"""
    engine = create_engine(database_url)
    session_factory = create_session_factory(engine)
    async with session_factory() as session:
        source = SourceRow(title="明通鑑", origin="测试", usage_terms="测试")
        session.add(source)
        await session.flush()
        version = TextVersionRow(
            source_id=source.id,
            label="卷029|抓取时间|sha256:abc",
            content="京師",
            content_sha256="abc",
        )
        session.add(version)
        conversation = ConversationRow(title="旧会话")
        session.add(conversation)
        await session.flush()
        message = MessageRow(
            conversation_id=conversation.id, role="assistant", status="done", content="旧回答"
        )
        session.add(message)
        await session.flush()
        session.add(
            MessageEventRow(
                message_id=message.id,
                seq=1,
                kind="citation_check",
                payload={
                    "statement": "京師指北京。",
                    "ok": True,
                    "citations": [
                        {
                            "version_id": str(version.id),
                            "start": 0,
                            "end": 2,
                            "exact_quote": "京師",
                            "ok": True,
                            "code": None,
                        }
                    ],
                },
            )
        )
        await session.commit()
        conversation_id = str(conversation.id)
    await engine.dispose()
    return conversation_id


async def test_stored_citations_gain_material_labels_on_read(
    chat_client: TestClient, database_url: str
) -> None:
    """旧会话的引文载荷没有作品与卷次：读取时补齐，界面才能显示材料·卷次。"""
    conversation_id = await _seed_old_citation(database_url)

    body = chat_client.get(f"/v1/conversations/{conversation_id}").json()

    citation = body["messages"][0]["events"][0]["payload"]["citations"][0]
    assert citation["work"] == "明通鑑"
    assert citation["volume"] == "卷029"
    assert citation["exact_quote"] == "京師"


async def test_legacy_citation_edge_cases_survive_reading(
    chat_client: TestClient, database_url: str
) -> None:
    """旧格式的畸形引文（非对象项、无 citations 字段）读取时原样保留，不报错。"""
    engine = create_engine(database_url)
    factory = create_session_factory(engine)
    async with factory() as session:
        conversation = ConversationRow(title="畸形旧会话")
        session.add(conversation)
        await session.flush()
        message = MessageRow(
            conversation_id=conversation.id, role="assistant", status="done", content="旧回答"
        )
        session.add(message)
        await session.flush()
        session.add_all(
            [
                MessageEventRow(
                    message_id=message.id,
                    seq=1,
                    kind="citation_check",
                    payload={
                        "statement": "缺字段",
                        "ok": False,
                        "citations": ["raw", {"exact_quote": "京師"}],
                    },
                ),
                MessageEventRow(
                    message_id=message.id,
                    seq=2,
                    kind="citation_check",
                    payload={"statement": "无引文数组", "ok": False},
                ),
            ]
        )
        await session.commit()
        conversation_id = str(conversation.id)
    await engine.dispose()

    body = chat_client.get(f"/v1/conversations/{conversation_id}").json()

    events = body["messages"][0]["events"]
    assert events[0]["payload"]["citations"] == [
        "raw",
        {"exact_quote": "京師", "work": "", "volume": ""},
    ]
    assert events[1]["payload"] == {"statement": "无引文数组", "ok": False}
