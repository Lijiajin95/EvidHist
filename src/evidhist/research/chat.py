"""对话循环（对话功能方案第 5 节）：PI 零工具，宿主代理工具并逐事件产出。

每一轮先让 PI 用 JSON 决定「调用工具还是收尾」；工具由调用方（`Toolbox`）执行，
结果回填后再问一次；收尾时先**流式**产出 Markdown 回答，再单独取一次结构化论断并
逐条做程序硬校验。未通过的论断如实报出，评审失败也如实记录。
"""

from __future__ import annotations

import json
from collections.abc import AsyncGenerator, Sequence
from dataclasses import dataclass, field
from typing import Protocol, cast

from evidhist.research.citations import ClaimVerdict, verify_claims
from evidhist.research.executor import RunLimits
from evidhist.research.pi_executor import parse_claims
from evidhist.research.pi_rpc import (
    PiConfig,
    TextDelta,
    add_tokens,
    ask_pi,
    extract_json,
    stream_pi,
)
from evidhist.research.report import ReportInput, render_report
from evidhist.research.review import Reviewer
from evidhist.research.tools import Material

TURNS_LIMIT = 4
DECIDE_MARKER = "请只输出下一步动作"
ANSWER_MARKER = "请用 Markdown 回答"
CLAIMS_MARKER = "请输出本轮论断与逐字引文"
TOOL_GUIDE = (
    "可用工具（只读）：\n"
    '- list_materials：{"arguments":{}}，列出已入库材料与字数\n'
    '- search：{"arguments":{"query":"检索词"}}，逐字子串检索\n'
    '- read：{"arguments":{"version_id":"…","start":0,"end":20}}，读指定区间\n'
    '- verify_citation：{"arguments":{"version_id":"…","start":0,"end":20,"exact_quote":"…"}}，'
    "程序硬校验\n"
    '- search_papers：{"arguments":{"query":"主题"}}，检索外部题录（OpenAlex、Crossref）\n'
    '- import_paper_record：{"arguments":{"index":0}}，把上一条检索结果的第 N 条题录入库'
)


@dataclass(frozen=True)
class ChatEvent:
    """一次可写入 message_events 并推给前端的结构化事件。"""

    kind: str
    payload: dict[str, object]


class Toolbox(Protocol):
    """宿主侧工具执行器；不认识的工具返回 ok=false，不抛异常。"""

    async def call(self, name: str, arguments: dict[str, object]) -> dict[str, object]: ...


@dataclass(frozen=True)
class ChatRequest:
    question: str
    materials: Sequence[Material]
    toolbox: Toolbox
    history: tuple[dict[str, str], ...] = ()
    reviewer: Reviewer | None = None
    run_id: str = ""


def _history_text(history: Sequence[dict[str, str]]) -> str:
    if not history:
        return "（无历史）"
    lines = [f"{item.get('role', 'user')}: {item.get('content', '')[:400]}" for item in history]
    return "\n".join(lines)


def decide_prompt(request: ChatRequest, results: Sequence[dict[str, object]]) -> str:
    return "\n".join(
        [
            "你是 EvidHist 的研究助手：历史材料只能通过工具读取，不得凭记忆作答。",
            f"{DECIDE_MARKER}（JSON，不要解释）：",
            '{"action":"tool","tool":"search","arguments":{"query":"于謙"}} 或 {"action":"final"}',
            f"研究问题：{request.question}",
            f"对话历史：\n{_history_text(request.history)}",
            TOOL_GUIDE,
            "已获得的工具结果：",
            json.dumps(results[-4:], ensure_ascii=False) if results else "（无）",
            "证据足够回答时立即输出 final；最多再用 4 轮。",
        ]
    )


def answer_prompt(request: ChatRequest, results: Sequence[dict[str, object]]) -> str:
    return "\n".join(
        [
            f"{ANSWER_MARKER}（Markdown，不要编造引文；只依据下列工具结果）：",
            f"研究问题：{request.question}",
            "工具结果（JSON）：",
            json.dumps(results, ensure_ascii=False),
            "要求：先给结论，再给依据（作品/卷次/区间），最后一句说明不确定之处；不得声称无法核实的内容。",
        ]
    )


def claims_prompt(request: ChatRequest, answer: str, results: Sequence[dict[str, object]]) -> str:
    return "\n".join(
        [
            f"{CLAIMS_MARKER}（JSON，不要解释）：",
            '{"claims":[{"statement":"…","citations":[{"version_id":"…","start":0,"end":20,'
            '"exact_quote":"…"}]}]}',
            "引文必须来自工具结果中给出的 version_id 与区间、逐字一致，长度 8-60 字："
            "只锁定「京師」这类关键词不算引文；没有可核查引文时输出 "
            '{"claims":[]}。',
            f"研究问题：{request.question}",
            f"回答草稿：{answer}",
            "工具结果（JSON）：",
            json.dumps(results, ensure_ascii=False),
        ]
    )


def _citation_payload(
    verdict: ClaimVerdict, labels: dict[str, tuple[str, str]]
) -> list[dict[str, object]]:
    """引文载荷带上作品与卷次，界面才能显示「明史·卷170」而不是一串 UUID。"""
    payloads: list[dict[str, object]] = []
    for item in verdict.citations:
        work, volume = labels.get(item.citation.version_id, ("", ""))
        payloads.append(
            {
                "version_id": item.citation.version_id,
                "start": item.citation.start,
                "end": item.citation.end,
                "exact_quote": item.citation.exact_quote,
                "ok": item.ok,
                "code": item.code,
                "work": work,
                "volume": volume,
            }
        )
    return payloads


@dataclass
class _RunState:
    """一轮对话的累计状态：工具结果、token 用量与最终回答。"""

    results: list[dict[str, object]] = field(default_factory=list[dict[str, object]])
    tokens: dict[str, int] = field(default_factory=lambda: {"input": 0, "output": 0})
    answer: str = ""
    claims: int = 0
    verified: int = 0


async def _stream_answer(
    config: PiConfig, request: ChatRequest, limits: RunLimits, state: _RunState
) -> AsyncGenerator[ChatEvent]:
    """流式产出回答增量；完整文本与用量记入状态。"""
    async for item in stream_pi(config, answer_prompt(request, state.results), limits):
        if isinstance(item, TextDelta):
            yield ChatEvent("token", {"text": item.text})
        else:
            state.answer = item.text
            add_tokens(state.tokens, item.usage)


async def _tool_turns(
    config: PiConfig, request: ChatRequest, limits: RunLimits, state: _RunState
) -> AsyncGenerator[ChatEvent]:
    """宿主代理的工具回合：PI 决定动作，宿主执行并回填结果。"""
    for _turn in range(TURNS_LIMIT):
        payload, usage = await ask_pi(config, decide_prompt(request, state.results), limits)
        add_tokens(state.tokens, usage)
        decision = extract_json(payload) or {}
        name = decision.get("tool")
        if decision.get("action") != "tool" or not isinstance(name, str):
            return
        arguments = decision.get("arguments")
        tool_args = cast("dict[str, object]", arguments) if isinstance(arguments, dict) else {}
        yield ChatEvent("tool_call", {"tool": name, "arguments": tool_args})
        outcome = await request.toolbox.call(name, tool_args)
        state.results.append({"tool": name, "result": outcome})
        yield ChatEvent("tool_result", {"tool": name, "result": outcome})


async def _verify_and_review(
    config: PiConfig, request: ChatRequest, limits: RunLimits, state: _RunState
) -> AsyncGenerator[ChatEvent]:
    """论断与引文逐条校验；配了评审器时再委托一次评审。"""
    reply, usage = await ask_pi(config, claims_prompt(request, state.answer, state.results), limits)
    add_tokens(state.tokens, usage)
    verdicts = verify_claims(request.materials, parse_claims(extract_json(reply) or {}))
    state.claims = len(verdicts)
    state.verified = sum(1 for verdict in verdicts if verdict.ok)
    labels = {
        material.version_id: (material.work, material.volume) for material in request.materials
    }
    for verdict in verdicts:
        yield ChatEvent(
            "citation_check",
            {
                "statement": verdict.statement,
                "ok": verdict.ok,
                "citations": _citation_payload(verdict, labels),
            },
        )
    if request.reviewer is None or not verdicts:
        return
    report = render_report(
        ReportInput(
            run_id=request.run_id or "chat-run",
            question=request.question,
            materials=request.materials,
            claims=verdicts,
        )
    )
    review = await request.reviewer.review(report, limits)
    yield ChatEvent(
        "review",
        {
            "verdict": review.verdict,
            "error": review.error,
            "comments": [dict(item) for item in review.comments],
        },
    )


async def stream_reply(
    config: PiConfig, request: ChatRequest, limits: RunLimits
) -> AsyncGenerator[ChatEvent]:
    """跑完一轮对话：工具回合 → 流式回答 → 论断校验 → 可选评审。"""
    state = _RunState()
    for stage in (_tool_turns, _stream_answer, _verify_and_review):
        async for event in stage(config, request, limits, state):
            yield event
    yield ChatEvent(
        "message_end",
        {
            "answer": state.answer,
            "usage": state.tokens,
            "claims": state.claims,
            "verified": state.verified,
        },
    )
