"""检索与解析不变量的单元测试。

这些内部函数决定"哪些片段进入模型、模型输出如何被采纳"：
检索词拆分、片段窗口、论断与引文的窄化解析、RPC 输出的容错解析。
它们不直接面向用户，但错一处就会把无关片段或畸形引文带进程序校验与评审。
"""

from __future__ import annotations

import asyncio
from pathlib import Path

import pytest

from evidhist.research.executor import BudgetedTools, RunLimitExceeded
from evidhist.research.pi_executor import (
    PiExecutor,
    _citations,
    _Hit,
    _passages,
    _search,
    _sentence_bounds,
    _string_list,
    _terms,
    _windows,
    parse_claims,
)
from evidhist.research.pi_rpc import (
    PiConfig,
    _decode,
    _env,
    _usage_of,
    add_tokens,
    as_int,
    extract_json,
)
from evidhist.research.tools import Material, ReadOnlyTools

MATERIALS = (
    Material(version_id="v-1", work="明史", volume="卷170", text="于謙守京師。也先入寇。"),
)


def _tools(calls: int = 40) -> BudgetedTools:
    return BudgetedTools(ReadOnlyTools(MATERIALS), calls)


def test_spaced_query_drops_single_character_terms() -> None:
    assert _terms("于謙 京師 戰 年") == ["于謙", "京師"]


def test_single_short_query_is_kept_and_long_query_is_dropped() -> None:
    assert _terms("于謙") == ["于謙"]
    assert _terms("這是一個非常長的檢索詞彙超過十二個字") == []


def test_string_list_ignores_non_lists_blank_and_non_string_items() -> None:
    assert _string_list("于謙") == []
    assert _string_list(["于謙", "  ", 7]) == ["于謙"]


def test_claims_require_statement_and_usable_citations() -> None:
    payload: dict[str, object] = {
        "claims": [
            {
                "statement": "有引文",
                "citations": [{"version_id": "v", "start": 0, "end": 2, "exact_quote": "于謙"}],
            },
            {"statement": "无引文", "citations": []},
            {"citations": [{"version_id": "v", "start": 0, "end": 2, "exact_quote": "于謙"}]},
            "not-an-object",
        ]
    }

    claims = parse_claims(payload)

    assert len(claims) == 1
    assert claims[0].statement == "有引文"


@pytest.mark.parametrize(
    "entry",
    [
        {"start": 0, "end": 2, "exact_quote": "于謙"},
        {"version_id": "v", "start": 0, "end": 2},
        {"version_id": "v", "end": 2, "exact_quote": "于謙"},
        {"version_id": "v", "start": "0", "end": 2, "exact_quote": "于謙"},
        "not-an-object",
    ],
)
def test_citations_drop_entries_missing_fields(entry: object) -> None:
    assert _citations([entry]) == ()


def test_sentence_bounds_expand_to_the_nearest_terminator() -> None:
    text = "前言。于謙守京師。後語"
    start, end = _sentence_bounds(text, text.index("于謙"), text.index("京師") + 2)

    assert (start, end) == (3, 9)  # 含句末「。」


def test_sentence_bounds_keep_the_window_when_no_terminator_exists() -> None:
    assert _sentence_bounds("于謙守京師", 0, 2) == (0, 2)


def test_windows_skip_hits_from_unknown_versions() -> None:
    hits = [_Hit(version_id="missing", start=0, end=2, terms={"于謙"})]

    assert _windows(hits, {"v-1": "于謙守京師"}) == {}


def test_neighbouring_hits_collapse_into_one_passage_read_through_the_tool() -> None:
    hits = [
        _Hit(version_id="v-1", start=index, end=index + 2, terms={"于謙"}) for index in range(12)
    ]

    passages = _passages(_tools(), hits, MATERIALS, max_calls=40)

    assert len(passages) == 1
    assert set(passages[0]) == {"version_id", "start", "end", "text"}
    assert passages[0]["text"] == MATERIALS[0].text


def test_search_stops_when_the_tool_budget_is_reached() -> None:
    hits = _search(_tools(calls=1), ["于謙", "京師"], max_calls=1)

    assert hits


def test_claims_prompt_carries_failed_verification_feedback(tmp_path: Path) -> None:
    from evidhist.research.executor import ResearchRequest

    executor = PiExecutor(
        PiConfig(
            provider="p",
            model="m",
            home=tmp_path,
            session_dir=tmp_path,
            workdir=tmp_path,
        )
    )
    request = ResearchRequest(
        question="q", materials=MATERIALS, attempt=2, feedback=("citation_failed",)
    )

    prompt = executor._claims_prompt(
        request, [{"version_id": "v-1", "start": 0, "end": 11, "text": "于謙守京師。"}]
    )

    assert "citation_failed" in prompt


def test_extract_json_tolerates_prose_and_rejects_broken_json() -> None:
    assert extract_json("没有 JSON") is None
    assert extract_json('坏的前缀 {"a": } 之后') is None
    assert extract_json('说明 {"a": 1} 结尾') == {"a": 1}


def test_decode_and_usage_helpers_are_defensive() -> None:
    assert _decode(b'{"type": "event"}') == {"type": "event"}
    assert _decode(b"not json") is None
    assert _decode(b"[1, 2]") is None
    assert _usage_of({"usage": "nope"}) == {}
    assert as_int("7") == 0
    assert as_int(None) == 0
    assert as_int(7) == 7


def test_add_tokens_accumulates_missing_keys() -> None:
    total = {"input": 1}

    add_tokens(total, {"input": 2, "output": 3})

    assert total == {"input": 3, "output": 3}


def test_env_prepends_the_pi_binary_directory(tmp_path: Path) -> None:
    config = PiConfig(
        provider="p",
        model="m",
        home=tmp_path,
        session_dir=tmp_path,
        workdir=tmp_path,
        bin_dir=tmp_path / "bin",
    )

    environment = _env(config)

    assert environment["PATH"].startswith(str(tmp_path / "bin"))
    assert environment["HOME"] == str(tmp_path)


def test_read_line_reports_timeout_as_a_run_limit() -> None:
    from evidhist.research.pi_rpc import _read_line

    class NeverEnding:
        async def readline(self) -> bytes:
            await asyncio.sleep(5)
            return b""

    class Process:
        stdout = NeverEnding()

    with pytest.raises(RunLimitExceeded) as error:
        asyncio.run(_read_line(Process(), timeout=0.01))  # type: ignore[arg-type]

    assert error.value.reason == "timeout"
