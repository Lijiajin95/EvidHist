"""对话工具的单元测试（对话功能方案第 5 节）。

固定四件事：引文校验走程序硬校验且不模糊匹配；题录正文与出处把来源库、链接和
检索时间写清楚；报告起草复用既有渲染并如实标记未通过的论断；评审委托失败时
记录为失败而不是通过。
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

import pytest

from evidhist.research.chat_tools import (
    paper_origin,
    paper_record_text,
    paper_usage_terms,
    request_review,
    verify_citation,
)
from evidhist.research.executor import ExecutorError, RunLimitExceeded, RunLimits
from evidhist.research.papers import PaperRecord
from evidhist.research.review import FakeReviewer, Reviewer, ReviewResult
from evidhist.research.tools import Material

MATERIALS = (Material(version_id="v-1", work="明史", volume="卷170", text="于謙字廷益，錢塘人。"),)
LIMITS = RunLimits(wall_seconds=30, idle_seconds=10)
RETRIEVED = datetime(2026, 10, 18, 12, 0, tzinfo=UTC)
RECORD = PaperRecord(
    sources=("openalex", "crossref"),
    title="The Defense of Beijing in 1449",
    authors=("Jiajin Li",),
    year=1998,
    venue="Ming Studies",
    doi="10.2307/1234",
    url="https://doi.org/10.2307/1234",
    retrieved_at=RETRIEVED,
)


def test_verify_citation_passes_for_an_exact_quote() -> None:
    result = verify_citation(MATERIALS, version_id="v-1", start=0, end=2, exact_quote="于謙")

    assert result["ok"] is True
    assert result["code"] is None
    assert result["exact_quote"] == "于謙"


def test_verify_citation_reports_a_quote_mismatch() -> None:
    result = verify_citation(MATERIALS, version_id="v-1", start=0, end=2, exact_quote="于謙傳")

    assert (result["ok"], result["code"]) == (False, "quote_mismatch")


def test_verify_citation_reports_an_unknown_version() -> None:
    result = verify_citation(MATERIALS, version_id="missing", start=0, end=2, exact_quote="于謙")

    assert (result["ok"], result["code"]) == (False, "unknown_version")


def test_paper_text_carries_the_bibliographic_fields() -> None:
    text = paper_record_text(RECORD)

    assert "The Defense of Beijing in 1449" in text
    assert "Jiajin Li" in text
    assert "1998" in text
    assert "Ming Studies" in text
    assert "10.2307/1234" in text


def test_paper_origin_and_terms_name_both_sources_and_the_retrieval_time() -> None:
    origin = paper_origin(RECORD)
    terms = paper_usage_terms(RECORD)

    assert "openalex" in origin
    assert "crossref" in origin
    assert "https://doi.org/10.2307/1234" in origin
    assert "2026-10-18" in origin
    assert "openalex" in terms
    assert "CC0" in terms
    assert len(terms) <= 500


async def test_request_review_returns_the_reviewer_verdict() -> None:
    result = await request_review(FakeReviewer(verdict="fail"), "报告正文", LIMITS)

    assert result.verdict == "fail"
    assert result.model == "fake-reviewer"


class _TimeOut:
    model = "broken"

    async def review(self, report_text: str, limits: RunLimits) -> ReviewResult:
        raise RunLimitExceeded("timeout")


class _ProtocolBroken:
    model = "broken"

    async def review(self, report_text: str, limits: RunLimits) -> ReviewResult:
        raise ExecutorError("garbage")


@pytest.mark.parametrize(
    ("reviewer", "expected"),
    [(_TimeOut(), "review_timeout"), (_ProtocolBroken(), "review_garbage")],
)
async def test_request_review_records_failures_instead_of_passing(
    reviewer: Reviewer, expected: str
) -> None:
    result = await request_review(reviewer, "报告正文", LIMITS)

    assert result.error == expected
    assert not result.ok


def test_minimal_record_omits_fields_it_does_not_have() -> None:
    minimal = PaperRecord(
        sources=("crossref",),
        title="京師守禦考",
        authors=(),
        year=None,
        venue="",
        doi=None,
        url="https://crossref.example/x",
        retrieved_at=RETRIEVED,
    )

    text = paper_record_text(minimal)
    terms = paper_usage_terms(minimal)

    assert "作者" not in text
    assert "年份" not in text
    assert "发表处" not in text
    assert "DOI" not in text
    assert "Crossref" in terms
    assert "CC0" not in terms


class _Unexpected:
    model = "broken"

    async def review(self, report_text: str, limits: RunLimits) -> ReviewResult:
        raise ValueError("boom")


async def test_request_review_records_unexpected_errors_as_failure() -> None:
    result = await request_review(_Unexpected(), "报告正文", LIMITS)

    assert result.error == "review_error_ValueError"
    assert not result.ok


class _StubSession:
    """对话工具的分发测试不需要数据库；入库路径由集成测试覆盖。"""


class _FakePaperClient:
    def __init__(self, payload: dict[str, Any]) -> None:
        self.payload = payload

    async def get(self, url: str, **_kwargs: Any) -> Any:
        payload = self.payload

        class Response:
            status_code = 200

            def json(self) -> dict[str, Any]:
                return payload

        return Response()


async def test_toolbox_dispatches_material_tools_and_reports_unknown_names() -> None:
    from evidhist.research.chat_tools import SessionToolbox
    from evidhist.research.tools import ReadOnlyTools

    toolbox = SessionToolbox(
        _StubSession(),  # type: ignore[arg-type]
        materials=MATERIALS,
        tools=ReadOnlyTools(MATERIALS),
        client=_FakePaperClient({}),
    )

    listed = await toolbox.call("list_materials", {})
    hits = await toolbox.call("search", {"query": "于謙"})
    read = await toolbox.call("read", {"version_id": "v-1", "start": 0, "end": 2})
    checked = await toolbox.call(
        "verify_citation",
        {"version_id": "v-1", "start": 0, "end": 2, "exact_quote": "于謙"},
    )
    unknown = await toolbox.call("shell_exec", {})

    assert listed["ok"] is True
    assert hits["ok"] is True and hits["hits"]
    assert read["ok"] is True and read["text"] == "于謙"
    assert checked["ok"] is True
    assert unknown == {"ok": False, "code": "unknown_tool", "tool": "shell_exec"}


async def test_toolbox_reports_bad_arguments_instead_of_raising() -> None:
    from evidhist.research.chat_tools import SessionToolbox
    from evidhist.research.tools import ReadOnlyTools

    toolbox = SessionToolbox(
        _StubSession(),  # type: ignore[arg-type]
        materials=MATERIALS,
        tools=ReadOnlyTools(MATERIALS),
        client=_FakePaperClient({}),
    )

    assert (await toolbox.call("search", {}))["code"] == "empty_query"
    assert (await toolbox.call("read", {"version_id": "v-1"}))["code"] == "invalid_range"
    assert (await toolbox.call("search_papers", {"query": " "}))["code"] == "empty_query"
    assert (await toolbox.call("import_paper_record", {"index": 3}))["code"] == (
        "paper_index_out_of_range"
    )


async def test_toolbox_searches_papers_and_keeps_them_for_import() -> None:
    from evidhist.research.chat_tools import SessionToolbox
    from evidhist.research.tools import ReadOnlyTools

    payload = {
        "results": [
            {
                "id": "https://openalex.org/W1",
                "doi": "https://doi.org/10.1/x",
                "title": "京师守御考",
                "publication_year": 2005,
                "authorships": [{"author": {"display_name": "王明"}}],
                "primary_location": {"source": {"display_name": "史学集刊"}},
            }
        ]
    }
    toolbox = SessionToolbox(
        _StubSession(),  # type: ignore[arg-type]
        materials=MATERIALS,
        tools=ReadOnlyTools(MATERIALS),
        client=_FakePaperClient(payload),
    )

    found = await toolbox.call("search_papers", {"query": "京师"})

    assert found["ok"] is True
    records = found["records"]
    assert isinstance(records, list) and records[0]["title"] == "京师守御考"
    assert records[0]["sources"] == ["openalex"]
    assert len(toolbox.last_papers) == 1


async def test_search_hits_carry_the_work_and_volume_labels() -> None:
    from evidhist.research.chat_tools import SessionToolbox
    from evidhist.research.tools import ReadOnlyTools

    toolbox = SessionToolbox(
        _StubSession(),  # type: ignore[arg-type]
        materials=MATERIALS,
        tools=ReadOnlyTools(MATERIALS),
        client=_FakePaperClient({}),
    )

    outcome = await toolbox.call("search", {"query": "于謙"})
    hits = outcome["hits"]
    assert isinstance(hits, list)
    first = hits[0]
    assert isinstance(first, dict)
    assert first["work"] == "明史"
    assert first["volume"] == "卷170"


def test_claims_prompt_requires_a_quotable_span() -> None:
    from evidhist.research.chat import ChatRequest, claims_prompt

    class _Toolbox:
        async def call(self, name: str, arguments: dict[str, object]) -> dict[str, object]:
            return {}

    prompt = claims_prompt(
        ChatRequest(question="问题", materials=MATERIALS, toolbox=_Toolbox()), "回答", []
    )

    assert "8-60 字" in prompt
    assert "关键词不算引文" in prompt
