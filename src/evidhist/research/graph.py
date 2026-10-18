"""最小研究闭环：LangGraph 小图（M03/M04）。

    准备 → 研究（执行器+只读工具） → 引用硬校验 ─┬─ 重试一次 → 研究
                                              └─ 反证记录 → 报告

失败即如实记录：超时/工具预算中止运行，引文反复不通过标为 insufficient，
都不以模型评分或"看起来合理"代替程序校验。
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable, Sequence
from dataclasses import dataclass, field
from typing import Any, TypedDict

# langgraph 不随包提供类型信息（无 py.typed/stub）：只在这段接线处显式使用 Any，
# 其余逻辑仍在 strict 模式下检查。
from langgraph.graph import END, StateGraph  # pyright: ignore[reportMissingTypeStubs]

from evidhist.research.citations import ClaimVerdict, verify_claims
from evidhist.research.executor import (
    BudgetedTools,
    ExecutorError,
    ResearchExecutor,
    ResearchRequest,
    RunLimitExceeded,
    RunLimits,
    Transcript,
)
from evidhist.research.report import ReportInput, render_report
from evidhist.research.review import Reviewer, ReviewResult, failed_review
from evidhist.research.tools import Material, ReadOnlyTools

Node = Callable[["ResearchState"], Awaitable["ResearchState"]]


class ResearchState(TypedDict, total=False):
    run_id: str
    question: str
    attempt: int
    feedback: tuple[str, ...]
    next_step: str
    stopped_reason: str | None
    transcript: Transcript | None
    verdicts: tuple[ClaimVerdict, ...]
    insufficient: tuple[str, ...]
    counter_scope: dict[str, object]
    report: str
    review: ReviewResult | None


@dataclass(frozen=True)
class ResearchResult:
    run_id: str
    question: str
    report: str
    claims: tuple[ClaimVerdict, ...] = ()
    insufficient: tuple[str, ...] = ()
    citation_index: tuple[dict[str, object], ...] = ()
    counter_scope: dict[str, object] = field(default_factory=dict[str, object])
    actions: tuple[dict[str, object], ...] = ()
    usage: dict[str, object] = field(default_factory=dict[str, object])
    stopped_reason: str | None = None
    attempts: int = 0
    tool_calls: int = 0
    review: ReviewResult | None = None
    materials: tuple[dict[str, object], ...] = ()
    raw_outputs: tuple[dict[str, object], ...] = ()


@dataclass
class RunContext:
    """一次运行内共享的工具预算、活动与用量记录。"""

    executor: ResearchExecutor
    limits: RunLimits
    materials: tuple[Material, ...]
    budgeted: BudgetedTools
    actions: list[dict[str, object]] = field(default_factory=list[dict[str, object]])
    usage: dict[str, object] = field(default_factory=dict[str, object])


def _counter_scope(transcript: Transcript | None) -> dict[str, object]:
    if transcript is None:
        return {"queries": [], "hits": 0, "findings": []}
    return {
        "queries": list(transcript.counter_queries),
        "hits": transcript.counter_hits,
        "findings": list(transcript.counter_findings),
    }


def _citation_index(
    verdicts: Sequence[ClaimVerdict], materials: Sequence[Material]
) -> tuple[dict[str, object], ...]:
    where = {material.version_id: (material.work, material.volume) for material in materials}
    index: list[dict[str, object]] = []
    for verdict in verdicts:
        for item in verdict.citations:
            work, volume = where.get(item.citation.version_id, ("未知", "未知"))
            index.append(
                {
                    "version_id": item.citation.version_id,
                    "work": work,
                    "volume": volume,
                    "start": item.citation.start,
                    "end": item.citation.end,
                    "exact_quote": item.citation.exact_quote,
                    "ok": item.ok,
                    "code": item.code,
                }
            )
    return tuple(index)


def _feedback(verdicts: Sequence[ClaimVerdict]) -> tuple[str, ...]:
    return tuple(
        f"{item.citation.version_id}:{item.code}"
        for verdict in verdicts
        for item in verdict.citations
        if not item.ok
    )


def prepare_node(context: RunContext) -> Node:
    async def prepare(state: ResearchState) -> ResearchState:
        if not context.materials:
            return {"stopped_reason": "no_materials"}
        context.actions.append(
            {
                "step": "prepare",
                "executor": context.executor.executor_name,
                "tools": ["list_materials", "search", "read", "exact_quote"],
                "materials": len(context.materials),
            }
        )
        return {"attempt": state.get("attempt", 1), "stopped_reason": None}

    return prepare


def investigate_node(context: RunContext) -> Node:
    async def investigate(state: ResearchState) -> ResearchState:
        request = ResearchRequest(
            question=state.get("question", ""),
            materials=context.materials,
            attempt=state.get("attempt", 1),
            feedback=state.get("feedback", ()),
        )
        try:
            transcript = await context.executor.investigate(
                request, context.budgeted, context.limits
            )
        except (RunLimitExceeded, ExecutorError) as error:
            context.actions.append({"step": "investigate", "stopped": error.reason})
            return {"stopped_reason": error.reason}
        context.usage.update(transcript.usage)
        context.actions.extend(transcript.actions)
        return {"transcript": transcript, "stopped_reason": None}

    return investigate


def verify_node(context: RunContext) -> Node:
    async def verify(state: ResearchState) -> ResearchState:
        transcript = state.get("transcript") or Transcript()
        verdicts = verify_claims(context.materials, transcript.claims)
        failing = [verdict for verdict in verdicts if not verdict.ok]
        attempt = state.get("attempt", 1)
        if failing and attempt <= context.limits.citation_retries:
            context.actions.append({"step": "verify", "result": "retry", "failing": len(failing)})
            return {
                "attempt": attempt + 1,
                "feedback": _feedback(failing),
                "next_step": "investigate",
            }
        context.actions.append({"step": "verify", "result": "done", "claims": len(verdicts)})
        return {
            "verdicts": verdicts,
            "insufficient": tuple(verdict.statement for verdict in failing),
            "feedback": (),
            "next_step": "counter_evidence",
        }

    return verify


def counter_node(context: RunContext) -> Node:
    async def counter_evidence(state: ResearchState) -> ResearchState:
        scope = _counter_scope(state.get("transcript"))
        context.actions.append({"step": "counter_evidence", "queries": scope["queries"]})
        return {"counter_scope": scope}

    return counter_evidence


def review_node(context: RunContext, reviewer: Reviewer | None) -> Node:
    async def review(state: ResearchState) -> ResearchState:
        if reviewer is None:
            context.actions.append({"step": "review", "result": "not_run"})
            return {"review": None}
        draft = render_report(
            ReportInput(
                run_id=state.get("run_id", ""),
                question=state.get("question", ""),
                materials=context.materials,
                claims=state.get("verdicts", ()),
                insufficient=state.get("insufficient", ()),
                counter_scope=state.get("counter_scope", _counter_scope(None)),
                stopped_reason=state.get("stopped_reason"),
            )
        )
        try:
            result = await reviewer.review(draft, context.limits)
        except (RunLimitExceeded, ExecutorError) as error:
            result = failed_review("pi", f"review_{error.reason}")
        context.actions.append({"step": "review", "verdict": result.verdict, "error": result.error})
        return {"review": result}

    return review


def compose_node(context: RunContext) -> Node:
    async def compose(state: ResearchState) -> ResearchState:
        report = render_report(
            ReportInput(
                run_id=state.get("run_id", ""),
                question=state.get("question", ""),
                materials=context.materials,
                claims=state.get("verdicts", ()),
                insufficient=state.get("insufficient", ()),
                counter_scope=state.get("counter_scope", _counter_scope(None)),
                stopped_reason=state.get("stopped_reason"),
                review=state.get("review"),
            )
        )
        return {"report": report}

    return compose


def _route_after_prepare(state: ResearchState) -> str:
    return "compose" if state.get("stopped_reason") else "investigate"


def _route_after_investigate(state: ResearchState) -> str:
    return "compose" if state.get("stopped_reason") else "verify"


def _route_after_verify(state: ResearchState) -> str:
    return state.get("next_step", "counter_evidence")


def _wire(nodes: dict[str, Node]) -> Any:
    graph: Any = StateGraph(ResearchState)
    for name, node in nodes.items():
        graph.add_node(name, node)
    graph.set_entry_point("prepare")
    graph.add_conditional_edges(
        "prepare", _route_after_prepare, {"investigate": "investigate", "compose": "compose"}
    )
    graph.add_conditional_edges(
        "investigate", _route_after_investigate, {"verify": "verify", "compose": "compose"}
    )
    graph.add_conditional_edges(
        "verify",
        _route_after_verify,
        {"investigate": "investigate", "counter_evidence": "counter_evidence"},
    )
    graph.add_edge("counter_evidence", "review")
    graph.add_edge("review", "compose")
    graph.add_edge("compose", END)
    compiled: Any = graph.compile()
    return compiled


def _raw_outputs(state: ResearchState) -> tuple[dict[str, object], ...]:
    transcript = state.get("transcript")
    return transcript.raw_outputs if transcript is not None else ()


def _to_result(state: ResearchState, context: RunContext) -> ResearchResult:
    verdicts = tuple(state.get("verdicts", ()))
    return ResearchResult(
        run_id=state.get("run_id", ""),
        question=state.get("question", ""),
        report=state.get("report", ""),
        claims=verdicts,
        insufficient=tuple(state.get("insufficient", ())),
        citation_index=_citation_index(verdicts, context.materials),
        counter_scope=dict(state.get("counter_scope", _counter_scope(None))),
        actions=tuple(context.actions),
        usage=dict(context.usage),
        stopped_reason=state.get("stopped_reason"),
        attempts=state.get("attempt", 1),
        tool_calls=context.budgeted.calls,
        review=state.get("review"),
        raw_outputs=_raw_outputs(state),
        materials=tuple(
            {
                "version_id": material.version_id,
                "work": material.work,
                "volume": material.volume,
                "chars": len(material.text),
            }
            for material in context.materials
        ),
    )


def build_graph(
    executor: ResearchExecutor,
    limits: RunLimits,
    materials: tuple[Material, ...],
    reviewer: Reviewer | None = None,
) -> Callable[[ResearchState], Awaitable[ResearchResult]]:
    """把执行器与材料绑定成一张小图；工具预算与活动记录在一次运行的上下文中累计。"""
    context = RunContext(
        executor=executor,
        limits=limits,
        materials=materials,
        budgeted=BudgetedTools(ReadOnlyTools(materials), limits.tool_calls),
    )
    compiled = _wire(
        {
            "prepare": prepare_node(context),
            "investigate": investigate_node(context),
            "verify": verify_node(context),
            "counter_evidence": counter_node(context),
            "review": review_node(context, reviewer),
            "compose": compose_node(context),
        }
    )

    async def invoke(state: ResearchState) -> ResearchResult:
        final: ResearchState = await compiled.ainvoke(state)
        return _to_result(final, context)

    return invoke


@dataclass(frozen=True)
class ResearchJob:
    """一次研究的输入：问题、运行标识、上限与可选评审器。"""

    question: str
    run_id: str
    limits: RunLimits = field(default_factory=RunLimits)
    reviewer: Reviewer | None = None


async def run_research(
    *, executor: ResearchExecutor, materials: Sequence[Material], job: ResearchJob
) -> ResearchResult:
    """跑一次研究闭环；材料为空时在调用任何模型之前拒绝。"""
    invoke = build_graph(executor, job.limits, tuple(materials), job.reviewer)
    return await invoke({"run_id": job.run_id, "question": job.question, "attempt": 1})
