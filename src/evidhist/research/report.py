"""研究报告渲染（M06）：人读 Markdown，原文记载与分析推断分开表述。

报告只呈现程序可复核的内容：论断、逐字引文与位置、程序校验结果、反证检索范围、
评审意见与人工复核栏；缺口与未知如实保留，不补写结论。
"""

from __future__ import annotations

import json
from collections.abc import Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, cast

if TYPE_CHECKING:  # 仅类型检查：运行时避免与 graph 循环导入
    from evidhist.research.graph import ResearchResult

from evidhist.research.citations import ClaimVerdict
from evidhist.research.review import ReviewResult
from evidhist.research.tools import Material

FAILED_MARK = "未通过程序校验"
RERUN_HINT = "请人工重跑"


@dataclass(frozen=True)
class ReportInput:
    """一次运行的报告输入；评审结果在评审步骤填入。"""

    run_id: str
    question: str
    materials: Sequence[Material]
    claims: Sequence[ClaimVerdict] = ()
    insufficient: Sequence[str] = ()
    counter_scope: dict[str, object] = field(default_factory=dict[str, object])
    stopped_reason: str | None = None
    review: ReviewResult | None = None


def render_report(data: ReportInput) -> str:
    parts = [
        f"# 研究报告：{data.question}",
        "",
        f"- 运行 ID：`{data.run_id}`",
        f"- 任务状态：{_status(data.stopped_reason)}",
        "",
        "> 表述分层：原文记载（引文）、论断支撑（程序校验）、历史判断与因果解释分别表达；",
        "> 本报告的引文只证明文字出自该版本该位置，不证明历史结论成立。",
        "",
        _materials_section(data.materials),
        _claims_section(data.claims, data.insufficient),
        _counter_section(data.counter_scope),
        _review_section(data.review),
        _review_checklist(),
        _stopped_section(data.stopped_reason),
    ]
    return "\n".join(parts)


def _status(stopped_reason: str | None) -> str:
    """明确区分「程序环节完成」与「研究结论已通过评审/复核」。"""
    if stopped_reason is not None:
        return f"**运行中止**（{stopped_reason}；未完成的论断不写入结论）"
    return "取数与程序校验已完成；模型评审与人工重点复核见 §4、§5，本报告不代表研究结论已通过评审"


def _materials_section(materials: Sequence[Material]) -> str:
    lines = ["## 1. 研究问题与材料范围", "", "只使用以下已入库材料，原文逐字保存、未改写：", ""]
    lines += [
        f"- 《{material.work}》{material.volume}（版本 `{material.version_id}`，{len(material.text)} 字）"
        for material in materials
    ]
    lines += ["", "三书可能存在共同出处或转引关系，不自动视为三份独立证据。", ""]
    return "\n".join(lines)


def _claims_section(claims: Sequence[ClaimVerdict], insufficient: Sequence[str]) -> str:
    lines = ["## 2. 主要论断与引文", ""]
    if not claims:
        lines += ["本次运行没有产生可呈现的论断。", ""]
        return "\n".join(lines)
    for index, verdict in enumerate(claims, start=1):
        mark = (
            "引文在该版本该位置逐字存在（**仅证明文字位置，不证明论断成立**）"
            if verdict.ok
            else f"**{FAILED_MARK}（{verdict.code}）**"
        )
        lines += [f"### 论断 {index}：{verdict.statement}", "", f"- 程序校验：{mark}"]
        for citation in verdict.citations:
            draft = citation.citation
            state = "已锁定" if citation.ok else f"拒绝（{citation.code}）"
            lines.append(
                f"- 引文（{state}）：`{draft.version_id}` 字符 {draft.start}-{draft.end}："
                f"「{draft.exact_quote}」"
            )
        lines.append("")
    if insufficient:
        lines += [
            f"以下论断未取得可复核引文，**不得当作已支撑结论**：{'；'.join(insufficient)}",
            "",
        ]
    return "\n".join(lines)


def _counter_section(counter_scope: dict[str, object]) -> str:
    raw_queries = counter_scope.get("queries", [])
    queries = (
        "、".join(str(query) for query in cast("list[object]", raw_queries))
        if isinstance(raw_queries, list)
        else ""
    ) or "（未记录）"
    raw_findings = counter_scope.get("findings", [])
    findings = (
        [str(finding) for finding in cast("list[object]", raw_findings)]
        if isinstance(raw_findings, list)
        else []
    )
    lines = [
        "## 3. 反证与替代解释",
        "",
        f"- 检索范围（查询词）：{queries}",
        f"- 命中数：{counter_scope.get('hits', 0)}",
    ]
    lines += [f"- 结果：{finding}" for finding in findings]
    lines += ["", "未找到反证不表示反证不存在；本次未检索其他来源。", ""]
    return "\n".join(lines)


def _review_section(review: ReviewResult | None) -> str:
    if review is None:
        return "## 4. 模型评审意见\n\n本次未运行评审（见运行记录）。\n"
    lines = [f"## 4. 模型评审意见（{review.model}）", "", f"- 判定：{review.verdict}"]
    lines += [
        f"- [{comment['severity']}] {comment['target']}：{comment['comment']}"
        for comment in review.comments
    ]
    if review.error:
        lines.append(f"- 评审失败：{review.error}（不视为通过）")
    lines.append("")
    return "\n".join(lines)


def _review_checklist() -> str:
    return "\n".join(
        [
            "## 5. 人工重点复核（用户填写）",
            "",
            "| 复核项 | 结论 | 备注 |",
            "| --- | --- | --- |",
            "| 核心结论 | 待复核 | |",
            "| 因果推断 | 待复核 | |",
            "| 争议与未知 | 待复核 | |",
            "",
        ]
    )


def _stopped_section(stopped_reason: str | None) -> str:
    if stopped_reason is None:
        return ""
    return "\n".join(
        [
            "## 6. 运行与失败说明",
            "",
            f"本次运行因 `{stopped_reason}` 停止，未完成的论断不写入结论，{RERUN_HINT}。",
            "",
        ]
    )


@dataclass(frozen=True)
class RunArtifacts:
    """一次运行落盘的产物位置。"""

    directory: Path
    paths: tuple[Path, ...]


def run_record(result: ResearchResult, *, executor_name: str, saved_at: str) -> dict[str, object]:
    """run.json 的内容：可获得的字段如实记录，取不到的记 null。"""
    review = result.review
    return {
        "run_id": result.run_id,
        "question": result.question,
        "executor": executor_name,
        "model": result.usage.get("model"),
        "saved_at": saved_at,
        "attempts": result.attempts,
        "tool_calls": result.tool_calls,
        "stopped_reason": result.stopped_reason,
        "insufficient": list(result.insufficient),
        "usage": result.usage,
        "counter_scope": result.counter_scope,
        "actions": list(result.actions),
        "materials": list(result.materials),
        "review": None
        if review is None
        else {
            "model": review.model,
            "verdict": review.verdict,
            "error": review.error,
            "checked_scope": review.checked_scope,
        },
    }


def save_run(
    directory: Path, result: ResearchResult, *, executor_name: str, saved_at: str
) -> RunArtifacts:
    """把报告、引文数据、运行记录与评审结果按次完整保存（M06）。"""
    directory.mkdir(parents=True, exist_ok=True)
    review = result.review
    files: dict[str, object] = {
        "report.md": result.report,
        "citations.json": {
            "run_id": result.run_id,
            "citations": list(result.citation_index),
            "insufficient": list(result.insufficient),
        },
        "run.json": run_record(result, executor_name=executor_name, saved_at=saved_at),
        "review.json": {
            "status": "not_run",
        }
        if review is None
        else {
            "status": "failed" if review.error else "done",
            "model": review.model,
            "verdict": review.verdict,
            "comments": list(review.comments),
            "checked_scope": review.checked_scope,
            "error": review.error,
            "raw_sha256": review.raw_sha256,
        },
    }
    if result.raw_outputs:
        files["pi_outputs.json"] = {"run_id": result.run_id, "outputs": list(result.raw_outputs)}
    paths: list[Path] = []
    for name, payload in files.items():
        path = directory / name
        if isinstance(payload, str):
            path.write_text(payload, encoding="utf-8")
        else:
            path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        paths.append(path)
    return RunArtifacts(directory=directory, paths=tuple(paths))
