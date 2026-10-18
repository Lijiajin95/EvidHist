"""运行产物保存的行为测试（离线，写临时目录）。

对应[最小技术方案](../docs/minimal-technical-plan-2026-10-18.md)§4.4/§9 M06：
报告、引文数据、运行记录、评审结果按次完整保存；取不到的字段记 null，不补写。
"""

from __future__ import annotations

import json
from pathlib import Path

from evidhist.research.executor import FakeExecutor, RunLimits
from evidhist.research.graph import ResearchJob, run_research
from evidhist.research.report import save_run
from evidhist.research.review import FakeReviewer, Reviewer
from evidhist.research.tools import Material

MATERIALS = (
    Material(version_id="v-170", work="明史", volume="卷170", text="于謙字廷益，錢塘人。"),
)


async def _run(tmp_path: Path, *, reviewer: Reviewer | None = None):
    return await run_research(
        executor=FakeExecutor(mode="ok"),
        materials=MATERIALS,
        job=ResearchJob(
            question="于謙是誰?",
            run_id="run-save",
            limits=RunLimits(),
            reviewer=reviewer,
        ),
    )


async def test_save_run_writes_four_artifacts(tmp_path: Path) -> None:
    result = await _run(tmp_path, reviewer=FakeReviewer(verdict="pass"))
    artifacts = save_run(
        tmp_path / "run-save", result, executor_name="fake", saved_at="2026-10-18T00:00:00Z"
    )
    names = sorted(path.name for path in artifacts.paths)
    assert names == ["citations.json", "report.md", "review.json", "run.json"]

    record = json.loads((artifacts.directory / "run.json").read_text(encoding="utf-8"))
    assert record["run_id"] == "run-save"
    assert record["executor"] == "fake"
    assert record["stopped_reason"] is None
    assert record["materials"] == [
        {"version_id": "v-170", "work": "明史", "volume": "卷170", "chars": 10}
    ]
    assert record["tool_calls"] > 0
    assert record["review"]["verdict"] == "pass"

    citations = json.loads((artifacts.directory / "citations.json").read_text(encoding="utf-8"))
    assert citations["citations"][0]["exact_quote"] == "于謙"
    assert citations["citations"][0]["version_id"] == "v-170"

    review = json.loads((artifacts.directory / "review.json").read_text(encoding="utf-8"))
    assert review["status"] == "done"
    assert review["verdict"] == "pass"

    report = (artifacts.directory / "report.md").read_text(encoding="utf-8")
    assert "于謙是誰?" in report
    assert "模型评审意见" in report


async def test_save_run_without_reviewer_records_not_run(tmp_path: Path) -> None:
    result = await _run(tmp_path)
    artifacts = save_run(tmp_path / "run-noreview", result, executor_name="fake", saved_at="now")
    review = json.loads((artifacts.directory / "review.json").read_text(encoding="utf-8"))
    assert review["status"] == "not_run"
    record = json.loads((artifacts.directory / "run.json").read_text(encoding="utf-8"))
    assert record["review"] is None
