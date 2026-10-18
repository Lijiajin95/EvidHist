"""研究闭环的组件测试：LangGraph 小图 + 执行器协议（离线，无数据库、无真实模型）。

对应[首版最小技术方案](../docs/minimal-technical-plan-2026-10-18.md)§5 与 §9：
正常路径产出可回查引文；引文失败重试一次后如实标为 insufficient；
超时与工具预算超限记录 stopped_reason 并保留已得产物。
"""

from __future__ import annotations

from evidhist.research.executor import FakeExecutor, RunLimitExceeded, RunLimits
from evidhist.research.graph import ResearchJob, run_research
from evidhist.research.review import FakeReviewer
from evidhist.research.tools import Material

MATERIALS = (
    Material(
        version_id="v-170",
        work="明史",
        volume="卷170",
        text="于謙字廷益，錢塘人。也先入寇，謙力主守京師，卒以守禦功著。",
    ),
    Material(
        version_id="v-032",
        work="明史紀事本末",
        volume="卷32",
        text="土木之變，京師震恐。于謙請守京師，人心稍定。",
    ),
)

QUESTION = "于謙在北京保衛戰中的作用是什麼?"


async def test_successful_run_verifies_every_citation_and_renders_report() -> None:
    result = await run_research(
        executor=FakeExecutor(mode="ok"),
        materials=MATERIALS,
        job=ResearchJob(
            question=QUESTION,
            run_id="run-ok",
            limits=RunLimits(),
        ),
    )
    assert result.stopped_reason is None
    assert result.insufficient == ()
    assert result.claims and all(claim.ok for claim in result.claims)
    assert result.attempts == 1
    assert result.tool_calls > 0
    assert result.usage["model"] == "fake"
    assert "于謙" in result.report
    assert QUESTION in result.report
    citation = result.claims[0].citations[0]
    assert citation.ok and citation.code is None
    assert any(
        entry["version_id"] == citation.citation.version_id for entry in result.citation_index
    )
    assert result.counter_scope["queries"]


async def test_persistently_tampered_quote_is_marked_insufficient_after_one_retry() -> None:
    result = await run_research(
        executor=FakeExecutor(mode="bad_quote"),
        materials=MATERIALS,
        job=ResearchJob(
            question=QUESTION,
            run_id="run-bad",
            limits=RunLimits(),
        ),
    )
    assert result.attempts == 2  # 初次 + 一次重试（RunLimits.citation_retries=1）
    assert result.stopped_reason is None
    assert result.insufficient
    assert all(not claim.ok for claim in result.claims)
    assert "未通过程序校验" in result.report


async def test_retry_recovers_when_second_attempt_is_verbatim() -> None:
    result = await run_research(
        executor=FakeExecutor(mode="bad_quote_once"),
        materials=MATERIALS,
        job=ResearchJob(
            question=QUESTION,
            run_id="run-retry",
            limits=RunLimits(),
        ),
    )
    assert result.attempts == 2
    assert result.insufficient == ()
    assert all(claim.ok for claim in result.claims)


async def test_timeout_is_recorded_without_fabricated_claims() -> None:
    result = await run_research(
        executor=FakeExecutor(mode="timeout"),
        materials=MATERIALS,
        job=ResearchJob(
            question=QUESTION,
            run_id="run-timeout",
            limits=RunLimits(),
        ),
    )
    assert result.stopped_reason == "timeout"
    assert result.claims == ()
    assert "人工重跑" in result.report


async def test_tool_budget_stops_the_run() -> None:
    result = await run_research(
        executor=FakeExecutor(mode="ok"),
        materials=MATERIALS,
        job=ResearchJob(
            question=QUESTION,
            run_id="run-budget",
            limits=RunLimits(tool_calls=1),
        ),
    )
    assert result.stopped_reason == "tool_budget"
    assert result.claims == ()


async def test_missing_materials_is_refused_before_any_model_call() -> None:
    executor = FakeExecutor(mode="ok")
    result = await run_research(
        executor=executor,
        materials=(),
        job=ResearchJob(
            question=QUESTION,
            run_id="run-empty",
            limits=RunLimits(),
        ),
    )
    assert result.stopped_reason == "no_materials"
    assert executor.calls == 0


class _TimeoutReviewer:
    """评审超时的替身：必须记为失败，而不是当作通过。"""

    async def review(self, report_text: str, limits: RunLimits):
        raise RunLimitExceeded("timeout")


async def test_review_node_records_verdict_into_report() -> None:
    result = await run_research(
        executor=FakeExecutor(mode="ok"),
        materials=MATERIALS,
        job=ResearchJob(
            question=QUESTION,
            run_id="run-review",
            limits=RunLimits(),
            reviewer=FakeReviewer(verdict="pass"),
        ),
    )
    assert result.review is not None and result.review.ok
    assert "模型评审意见" in result.report
    assert "fake-reviewer" in result.report


async def test_missing_reviewer_is_recorded_as_not_run() -> None:
    result = await run_research(
        executor=FakeExecutor(mode="ok"),
        materials=MATERIALS,
        job=ResearchJob(
            question=QUESTION,
            run_id="run-no-review",
            limits=RunLimits(),
        ),
    )
    assert result.review is None
    assert "本次未运行评审" in result.report


async def test_reviewer_timeout_is_recorded_as_failed_review() -> None:
    result = await run_research(
        executor=FakeExecutor(mode="ok"),
        materials=MATERIALS,
        job=ResearchJob(
            question=QUESTION,
            run_id="run-review-timeout",
            limits=RunLimits(),
            reviewer=_TimeoutReviewer(),
        ),
    )
    assert result.review is not None
    assert result.review.ok is False
    assert result.review.error == "review_timeout"
    assert "评审失败" in result.report
