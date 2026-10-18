"""单模型评审的结果契约与严格解析（M05）。

评审模型只看报告与引文上下文，不自行检索材料；输出必须是本文件的严格契约。
缺评、缺字段或非法判定一律记为失败，**不自动视为通过**。
"""

from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
from typing import Literal, Protocol, cast

from evidhist.research.executor import ExecutorError, RunLimitExceeded, RunLimits
from evidhist.research.pi_rpc import PiConfig, ask_pi, extract_json

VERDICTS = ("pass", "fail", "insufficient")
SEVERITIES = ("info", "warn", "error")


class ReviewFormatError(ValueError):
    """评审输出不符合契约；调用方记录 review_failed。"""


@dataclass(frozen=True)
class ReviewResult:
    model: str
    verdict: Literal["pass", "fail", "insufficient"]
    comments: tuple[dict[str, str], ...] = ()
    checked_scope: str = ""
    error: str | None = None
    raw_sha256: str = ""

    @property
    def ok(self) -> bool:
        return self.error is None and self.verdict == "pass"


def parse_review(payload: object, *, model: str, raw_sha256: str = "") -> ReviewResult:
    """按 §4.5 契约解析评审输出；任何不符都抛 `ReviewFormatError`。"""
    if not isinstance(payload, dict):
        raise ReviewFormatError("review_not_object")
    data = cast("dict[str, object]", payload)
    verdict = data.get("verdict")
    if not isinstance(verdict, str) or verdict not in VERDICTS:
        raise ReviewFormatError("invalid_verdict")
    raw_comments = data.get("comments", [])
    if not isinstance(raw_comments, list):
        raise ReviewFormatError("comments_not_list")
    comments = _parse_comments(cast("list[object]", raw_comments))
    scope = data.get("checked_scope", "")
    if not isinstance(scope, str):
        raise ReviewFormatError("scope_not_string")
    return ReviewResult(
        model=model,
        verdict=verdict,
        comments=tuple(comments),
        checked_scope=scope,
        raw_sha256=raw_sha256,
    )


def failed_review(model: str, error: str) -> ReviewResult:
    """评审不可用或缺评时的显式失败记录。"""
    return ReviewResult(model=model, verdict="insufficient", comments=(), error=error)


def _parse_comments(raw_comments: list[object]) -> list[dict[str, str]]:
    comments: list[dict[str, str]] = []
    for item in raw_comments:
        if not isinstance(item, dict):
            raise ReviewFormatError("comment_not_object")
        entry = cast("dict[str, object]", item)
        severity = entry.get("severity")
        if not isinstance(severity, str) or severity not in SEVERITIES:
            raise ReviewFormatError("invalid_severity")
        target, comment = entry.get("target"), entry.get("comment")
        if not isinstance(target, str) or not isinstance(comment, str):
            raise ReviewFormatError("comment_fields_missing")
        comments.append({"target": target, "severity": severity, "comment": comment})
    return comments


class Reviewer(Protocol):
    """评审器协议：只看报告文本，不接触材料工具。"""

    async def review(self, report_text: str, limits: RunLimits) -> ReviewResult: ...


@dataclass(frozen=True)
class FakeReviewer:
    """确定性评审器：供组件测试与干跑使用。"""

    verdict: Literal["pass", "fail", "insufficient"] = "pass"
    comment: str = "引文与论断一致，未见明显越界表述。"
    model_name: str = "fake-reviewer"

    async def review(self, report_text: str, limits: RunLimits) -> ReviewResult:
        return ReviewResult(
            model=self.model_name,
            verdict=self.verdict,
            comments=({"target": "报告", "severity": "info", "comment": self.comment},),
            checked_scope="报告全文与引文位置",
        )


@dataclass(frozen=True)
class PiReviewer:
    """单模型评审：用 PI（零工具）读报告与引文上下文，按 §4.5 契约返回。"""

    config: PiConfig

    async def review(self, report_text: str, limits: RunLimits) -> ReviewResult:
        prompt = review_prompt(report_text)
        try:
            text, _usage = await ask_pi(self.config, prompt, limits)
        except (RunLimitExceeded, ExecutorError) as error:
            return failed_review(self.config.model, f"review_{error.reason}")
        try:
            return parse_review(
                extract_json(text),
                model=self.config.model,
                raw_sha256=sha256(text.encode()).hexdigest(),
            )
        except ReviewFormatError as error:
            return failed_review(self.config.model, f"review_{error}")


def review_prompt(report_text: str) -> str:
    return "\n".join(
        [
            "你是历史研究评审。下面是一份研究报告；请检查：引文是否支持对应论断、",
            "原文记载与分析推断是否分开表述、反证与未知是否如实保留、是否存在越界的历史结论。",
            "只输出 JSON，不要解释：",
            '{"verdict":"pass|fail|insufficient","checked_scope":"...",'
            '"comments":[{"target":"...","severity":"info|warn|error","comment":"..."}]}',
            "报告如下：",
            report_text,
        ]
    )
