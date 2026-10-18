"""单模型评审的契约测试（M05）：解析、失败记录与 PI 评审器行为。

对应[最小技术方案](../docs/minimal-technical-plan-2026-10-18.md)§4.5：
输出必须严格符合契约；缺评、字段不符或超时一律记为失败，绝不自动视为通过。
"""

from __future__ import annotations

import stat
from pathlib import Path

import pytest

from evidhist.research.executor import RunLimits
from evidhist.research.pi_rpc import PiConfig
from evidhist.research.review import (
    FakeReviewer,
    PiReviewer,
    ReviewFormatError,
    failed_review,
    parse_review,
    review_prompt,
)

REPO = Path(__file__).resolve().parents[2]
FAKE_PI = REPO / "tests" / "fixtures" / "fake_pi.py"
LIMITS = RunLimits(wall_seconds=30, idle_seconds=10)


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


def test_valid_review_is_parsed_with_comments() -> None:
    result = parse_review(
        {
            "verdict": "fail",
            "checked_scope": "报告 §1-§3",
            "comments": [{"target": "§2", "severity": "error", "comment": "引文不支持论断。"}],
        },
        model="m",
        raw_sha256="ab",
    )

    assert result.verdict == "fail"
    assert result.checked_scope == "报告 §1-§3"
    assert result.comments == (
        {"target": "§2", "severity": "error", "comment": "引文不支持论断。"},
    )
    assert result.raw_sha256 == "ab"
    assert not result.ok


def test_missing_comments_and_scope_default_to_empty() -> None:
    result = parse_review({"verdict": "pass"}, model="m")

    assert result.comments == ()
    assert result.checked_scope == ""
    assert result.error is None
    assert result.ok


@pytest.mark.parametrize(
    ("payload", "code"),
    [
        (["not", "an", "object"], "review_not_object"),
        ({}, "invalid_verdict"),
        ({"verdict": "maybe"}, "invalid_verdict"),
        ({"verdict": 3}, "invalid_verdict"),
        ({"verdict": "pass", "comments": "none"}, "comments_not_list"),
        ({"verdict": "pass", "checked_scope": 7}, "scope_not_string"),
        ({"verdict": "pass", "comments": ["x"]}, "comment_not_object"),
        (
            {"verdict": "pass", "comments": [{"severity": "fatal", "target": "t", "comment": "c"}]},
            "invalid_severity",
        ),
        (
            {"verdict": "pass", "comments": [{"severity": "info", "target": "t"}]},
            "comment_fields_missing",
        ),
        (
            {"verdict": "pass", "comments": [{"severity": "info", "comment": "c"}]},
            "comment_fields_missing",
        ),
    ],
)
def test_contract_violations_are_rejected(payload: object, code: str) -> None:
    with pytest.raises(ReviewFormatError) as error:
        parse_review(payload, model="m")

    assert str(error.value) == code


def test_failed_review_never_counts_as_pass() -> None:
    result = failed_review("m", "review_timeout")

    assert result.verdict == "insufficient"
    assert result.error == "review_timeout"
    assert not result.ok


async def test_fake_reviewer_returns_its_verdict() -> None:
    result = await FakeReviewer(verdict="fail").review("报告", LIMITS)

    assert result.verdict == "fail"
    assert result.ok is False


async def test_fake_reviewer_pass_is_ok() -> None:
    result = await FakeReviewer().review("报告", LIMITS)

    assert result.ok is True
    assert result.comments[0]["severity"] == "info"


async def test_pi_reviewer_parses_a_valid_reply(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("FAKE_PI_MODE", "ok")

    result = await PiReviewer(config(tmp_path)).review("报告正文", LIMITS)

    assert result.verdict == "pass"
    assert result.ok is True
    assert len(result.raw_sha256) == 64


async def test_pi_reviewer_records_protocol_failure(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("FAKE_PI_MODE", "garbage")

    result = await PiReviewer(config(tmp_path)).review("报告正文", LIMITS)

    assert result.verdict == "insufficient"
    assert result.error == "review_review_not_object"
    assert not result.ok


async def test_pi_reviewer_records_timeout(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("FAKE_PI_MODE", "unsettled")

    result = await PiReviewer(config(tmp_path)).review("报告正文", LIMITS)

    assert result.error == "review_timeout"
    assert not result.ok


def test_review_prompt_carries_the_report() -> None:
    prompt = review_prompt("论断 1：于謙主張固守。")

    assert "论断 1：于謙主張固守。" in prompt
    assert "verdict" in prompt
