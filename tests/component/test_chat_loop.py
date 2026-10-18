"""对话循环的组件测试：工具由宿主执行、回答真实流式、引文逐条校验（离线假 PI）。

对应[对话功能方案](../docs/chat-feature-plan-2026-10-18.md)第 5 节：事件顺序、工具预算、
未通过校验的引文如实上报、评审失败不视为通过。
"""

from __future__ import annotations

import stat
from pathlib import Path

import pytest

from evidhist.research.chat import TURNS_LIMIT, ChatRequest, stream_reply
from evidhist.research.executor import RunLimits
from evidhist.research.pi_rpc import PiConfig
from evidhist.research.review import FakeReviewer
from evidhist.research.tools import Material

REPO = Path(__file__).resolve().parents[2]
FAKE_PI = REPO / "tests" / "fixtures" / "fake_pi.py"
MATERIALS = (Material(version_id="v-1", work="明史", volume="卷170", text="于謙字廷益，錢塘人。"),)
LIMITS = RunLimits(wall_seconds=30, idle_seconds=5)


class FakeToolbox:
    """记录宿主侧的工具调用，返回一条可引用的命中。"""

    def __init__(self, *, fail: bool = False) -> None:
        self.calls: list[tuple[str, dict[str, object]]] = []
        self.fail = fail

    async def call(self, name: str, arguments: dict[str, object]) -> dict[str, object]:
        self.calls.append((name, arguments))
        if self.fail:
            return {"ok": False, "code": "unknown_tool"}
        return {
            "ok": True,
            "hits": [{"version_id": "v-1", "start": 0, "end": 2, "exact_quote": "于謙"}],
        }


def config(tmp_path: Path) -> PiConfig:
    FAKE_PI.chmod(FAKE_PI.stat().st_mode | stat.S_IXUSR)
    return PiConfig(
        provider="fake-provider",
        model="fake-model",
        home=tmp_path / "home",
        session_dir=tmp_path / "sessions",
        workdir=tmp_path,
        command=str(FAKE_PI),
    )


async def collect(tmp_path: Path, request: ChatRequest) -> list[tuple[str, dict[str, object]]]:
    events: list[tuple[str, dict[str, object]]] = []
    async for event in stream_reply(config(tmp_path), request, LIMITS):
        events.append((event.kind, event.payload))
    return events


async def test_tool_calls_tokens_and_citation_checks_come_in_order(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("FAKE_PI_MODE", "ok")
    toolbox = FakeToolbox()
    request = ChatRequest(
        question="于謙在守禦中的作用?", materials=MATERIALS, toolbox=toolbox, run_id="c-1"
    )

    events = await collect(tmp_path, request)
    kinds = [kind for kind, _payload in events]

    assert kinds[0] == "tool_call"
    assert kinds[1] == "tool_result"
    assert "token" in kinds
    assert "citation_check" in kinds
    assert kinds[-1] == "message_end"
    assert toolbox.calls[0][0] == "search"

    tokens = "".join(str(payload["text"]) for kind, payload in events if kind == "token")
    assert "于謙" in tokens
    check = next(payload for kind, payload in events if kind == "citation_check")
    assert check["ok"] is True
    end = events[-1][1]
    assert end["claims"] == 1
    assert end["verified"] == 1


async def test_a_failing_citation_is_reported_and_never_counted_as_verified(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("FAKE_PI_MODE", "ok")
    materials = (Material(version_id="v-1", work="明史", volume="卷170", text="于謙字廷益。"),)

    # 假 PI 的引文取自工具结果；这里让结果给出错误原文，校验必须失败
    class MismatchingToolbox(FakeToolbox):
        async def call(self, name: str, arguments: dict[str, object]) -> dict[str, object]:
            await super().call(name, arguments)
            return {
                "ok": True,
                "hits": [{"version_id": "v-1", "start": 0, "end": 2, "exact_quote": "于謙傳"}],
            }

    events = await collect(
        tmp_path, ChatRequest(question="问题", materials=materials, toolbox=MismatchingToolbox())
    )

    check = next(payload for kind, payload in events if kind == "citation_check")
    assert check["ok"] is False
    assert events[-1][1]["verified"] == 0


async def test_the_tool_loop_stops_at_the_turn_limit(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("FAKE_PI_MODE", "ok")
    request = ChatRequest(question="FORCE_TOOL 问题", materials=MATERIALS, toolbox=FakeToolbox())

    events = await collect(tmp_path, request)

    tool_calls = [kind for kind, _payload in events if kind == "tool_call"]
    assert len(tool_calls) == TURNS_LIMIT
    assert events[-1][0] == "message_end"


async def test_a_reviewer_adds_a_review_event(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("FAKE_PI_MODE", "ok")
    request = ChatRequest(
        question="问题",
        materials=MATERIALS,
        toolbox=FakeToolbox(),
        reviewer=FakeReviewer(verdict="fail"),
    )

    events = await collect(tmp_path, request)

    review = next(payload for kind, payload in events if kind == "review")
    assert review["verdict"] == "fail"
    assert review["comments"]


async def test_usage_is_accumulated_across_the_three_calls(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("FAKE_PI_MODE", "ok")
    request = ChatRequest(question="问题", materials=MATERIALS, toolbox=FakeToolbox())

    events = await collect(tmp_path, request)

    usage = events[-1][1]["usage"]
    assert isinstance(usage, dict)
    # 两次决定动作（先检索、再收尾）、一次流式回答、一次论断校验（每次 120/30）
    assert usage["input"] == 480
    assert usage["output"] == 120
