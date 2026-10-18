"""执行器协议与确定性测试替身（M03/M07）。

- 执行器**只通过只读工具**接触材料：`BudgetedTools` 计费并限制调用次数，超限即停止。
- `PiExecutor`（见 `pi_executor.py`）与 `FakeExecutor` 实现同一协议；
  图、引用校验与报告都不依赖具体执行器。
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field
from typing import Protocol

from evidhist.research.citations import CitationDraft, ClaimDraft
from evidhist.research.tools import Material, ReadOnlyTools, ToolError


class RunLimitExceeded(Exception):
    """达到时间/工具预算等运行上限；调用方据此记录 stopped_reason。"""

    def __init__(self, reason: str) -> None:
        self.reason = reason
        super().__init__(reason)


class ExecutorError(Exception):
    """执行器明确失败（协议错误、进程退出、模型报错）；调用方如实记录，不假装成功。"""

    def __init__(self, reason: str) -> None:
        self.reason = reason
        super().__init__(reason)


@dataclass(frozen=True)
class RunLimits:
    wall_seconds: int = 1200
    tool_calls: int = 60
    idle_seconds: int = 120
    citation_retries: int = 1


@dataclass(frozen=True)
class ResearchRequest:
    question: str
    materials: tuple[Material, ...]
    attempt: int = 1
    feedback: tuple[str, ...] = ()


@dataclass(frozen=True)
class Transcript:
    claims: tuple[ClaimDraft, ...] = ()
    queries: tuple[str, ...] = ()
    counter_queries: tuple[str, ...] = ()
    counter_findings: tuple[str, ...] = ()
    counter_hits: int = 0
    raw_outputs: tuple[dict[str, object], ...] = ()
    notes: str = ""
    actions: tuple[dict[str, object], ...] = ()
    usage: dict[str, object] = field(default_factory=dict[str, object])
    duration_seconds: float = 0.0


class ResearchExecutor(Protocol):
    executor_name: str

    async def investigate(
        self, request: ResearchRequest, tools: BudgetedTools, limits: RunLimits
    ) -> Transcript: ...


class BudgetedTools:
    """只读工具的预算包装：每次调用计数，超过上限抛 `RunLimitExceeded("tool_budget")`。"""

    def __init__(self, tools: ReadOnlyTools, limit: int) -> None:
        self._tools = tools
        self._limit = limit
        self.calls = 0

    def list_materials(self) -> list[dict[str, object]]:
        self._charge()
        return self._tools.list_materials()

    def search(
        self, query: str, version_ids: Sequence[str] | None = None, limit: int = 20
    ) -> list[dict[str, object]]:
        self._charge()
        return self._tools.search(query, version_ids=version_ids, limit=limit)

    def read(self, version_id: str, start: int, end: int) -> dict[str, object]:
        self._charge()
        return self._tools.read(version_id, start, end)

    def exact_quote(self, version_id: str, start: int, end: int) -> str:
        self._charge()
        return self._tools.exact_quote(version_id, start, end)

    def _charge(self) -> None:
        self.calls += 1
        if self.calls > self._limit:
            raise RunLimitExceeded("tool_budget")


class FakeExecutor:
    """确定性执行器：从只读工具取真实片段，按 `mode` 注入失败，供组件测试与干跑使用。"""

    executor_name = "fake"

    def __init__(self, mode: str = "ok") -> None:
        self.mode = mode
        self.calls = 0
        self.feedback_seen: list[tuple[str, ...]] = []

    async def investigate(
        self, request: ResearchRequest, tools: BudgetedTools, limits: RunLimits
    ) -> Transcript:
        self.calls += 1
        self.feedback_seen.append(request.feedback)
        if self.mode == "timeout":
            raise RunLimitExceeded("timeout")
        queries = ("于謙", "土木之變")
        hits = [hit for query in queries for hit in tools.search(query, limit=5)]
        counter_queries = ("也先", "京師")
        counter_hits = [hit for query in counter_queries for hit in tools.search(query, limit=5)]
        claim = self._claim(tools, hits, tamper=self._tamper(request))
        return Transcript(
            claims=(claim,) if claim is not None else (),
            queries=queries,
            counter_queries=counter_queries,
            counter_findings=(
                f"反证检索命中 {len(counter_hits)} 处"
                if counter_hits
                else "未找到反证（不等于不存在）",
            ),
            counter_hits=len(counter_hits),
            notes=f"fake executor mode={self.mode}",
            actions=(
                {"tool": "search", "queries": list(queries), "hits": len(hits)},
                {"tool": "search", "queries": list(counter_queries), "hits": len(counter_hits)},
            ),
            usage={"model": "fake", "input_tokens": 0, "output_tokens": 0, "calls": 1},
            duration_seconds=0.0,
        )

    def _tamper(self, request: ResearchRequest) -> bool:
        if self.mode == "bad_quote":
            return True
        return self.mode == "bad_quote_once" and request.attempt == 1

    def _claim(
        self, tools: BudgetedTools, hits: list[dict[str, object]], *, tamper: bool
    ) -> ClaimDraft | None:
        usable = [hit for hit in hits if hit["version_id"] != "unused"][:2]
        if not usable:
            return None
        citations = tuple(self._citation(tools, hit, tamper) for hit in usable)
        return ClaimDraft(statement="于謙在京城守禦中主張固守，京師人心稍定。", citations=citations)

    def _citation(
        self, tools: BudgetedTools, hit: dict[str, object], tamper: bool
    ) -> CitationDraft:
        version_id = str(hit["version_id"])
        start, end = hit.get("start"), hit.get("end")
        if not isinstance(start, int) or not isinstance(end, int):
            raise ToolError("invalid_hit")
        quote = tools.exact_quote(version_id, start, end)
        if tamper:
            quote = ("甲" if quote[-1] != "甲" else "乙") + quote[1:] if len(quote) > 1 else "甲"
        return CitationDraft(version_id=version_id, start=start, end=end, exact_quote=quote)
