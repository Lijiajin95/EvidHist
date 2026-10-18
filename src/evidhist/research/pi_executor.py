"""Pi 薄适配：以 RPC 子进程运行 PI，工具调用由本适配器代理（M03/M07）。

设计要点（与[最小技术方案](../../../docs/minimal-technical-plan-2026-10-18.md)§4.3/§6 一致）：

- **PI 本体零工具**：以 `--no-tools --no-mcp --no-extensions --no-skills --no-context-files`
  启动，PI 无法执行 shell、读写文件或联网；材料只能经本适配器调用只读工具取得。
- **宿主侧代理**：三次 PI 调用（检索计划 → 论断与引文 → 反证归纳），中间的材料访问
  全部走 `BudgetedTools`，工具调用次数计入运行预算。
- **失败如实上报**：超时抛 `RunLimitExceeded("timeout")`，协议/模型错误抛 `ExecutorError`，
  不自动重跑、不补写结果。
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass
from typing import cast

from evidhist.research.citations import CitationDraft, ClaimDraft
from evidhist.research.executor import (
    BudgetedTools,
    ExecutorError,
    ResearchRequest,
    RunLimits,
    Transcript,
)
from evidhist.research.pi_rpc import PiConfig, add_tokens, as_int, ask_pi, extract_json
from evidhist.research.tools import Material

HITS_PER_QUERY = 3
SNIPPET_LIMIT = 16
WINDOW_CHARS = 110
PASSAGE_LIMIT = 8
SENTENCE_CHARS = 160
_SENTENCE_END = ("\u3002", "\u300d", "\uff01", "\uff1f")  # 中文句末标点


class PiExecutor:
    """把 PI 的三次调用翻译成一次 `Transcript`。"""

    executor_name = "pi"

    def __init__(self, config: PiConfig) -> None:
        self.config = config

    async def investigate(
        self, request: ResearchRequest, tools: BudgetedTools, limits: RunLimits
    ) -> Transcript:
        started = time.monotonic()
        tokens = {"input": 0, "output": 0}
        raw: list[dict[str, object]] = []
        budget = max(6, limits.tool_calls)
        plan = await self._record(raw, tokens, "plan", self._plan_prompt(request), limits)
        queries = _string_list(plan.get("queries"))
        counter_queries = _string_list(plan.get("counter_queries"))
        hits, passages, counter_hits, counter_passages = self._retrieve(
            tools, queries, counter_queries, request.materials, budget
        )
        claims = await self._record(
            raw, tokens, "claims", self._claims_prompt(request, passages), limits
        )
        findings = await self._record(
            raw, tokens, "counter", self._counter_prompt(claims, counter_passages), limits
        )
        return Transcript(
            claims=parse_claims(claims),
            queries=tuple(queries),
            counter_queries=tuple(counter_queries),
            counter_findings=tuple(_string_list(findings.get("findings"))),
            counter_hits=len(counter_hits),
            raw_outputs=tuple(raw),
            notes="pi",
            actions=(
                {
                    "tool": "search",
                    "queries": queries,
                    "hits": len(hits),
                    "passages": len(passages),
                },
                {
                    "tool": "search",
                    "queries": counter_queries,
                    "hits": len(counter_hits),
                    "passages": len(counter_passages),
                },
            ),
            usage={
                "model": self.config.model,
                "provider": self.config.provider,
                "calls": 3,
                "input_tokens": tokens["input"],
                "output_tokens": tokens["output"],
            },
            duration_seconds=time.monotonic() - started,
        )

    async def _record(
        self,
        raw: list[dict[str, object]],
        tokens: dict[str, int],
        stage: str,
        prompt: str,
        limits: RunLimits,
    ) -> dict[str, object]:
        """跑一次 PI 调用：累计 token 与原始输出，返回解析后的 JSON。"""
        payload, usage, text = await self._ask_json(prompt, limits, stage=stage)
        add_tokens(tokens, usage)
        raw.append({"stage": stage, "text": text[:8000]})
        return payload

    def _retrieve(
        self,
        tools: BudgetedTools,
        queries: list[str],
        counter_queries: list[str],
        materials: tuple[Material, ...],
        budget: int,
    ) -> tuple[list[_Hit], list[dict[str, object]], list[_Hit], list[dict[str, object]]]:
        """按预算分工检索正文与反证片段：搜索 1/3、正文片段 2/3、反证用剩余额度。"""
        hits = _search(tools, queries, max_calls=budget // 3)
        passages = _passages(tools, hits, materials, max_calls=budget * 2 // 3)
        counter_hits = _search(tools, counter_queries, max_calls=budget * 5 // 6)
        counter_passages = _passages(tools, counter_hits, materials, max_calls=budget)
        return hits, passages, counter_hits, counter_passages

    async def _ask_json(
        self, prompt: str, limits: RunLimits, *, stage: str
    ) -> tuple[dict[str, object], dict[str, int], str]:
        text, usage = await self._prompt(prompt, limits)
        payload = extract_json(text)
        if payload is None:
            raise ExecutorError(f"{stage}_not_json")
        return payload, usage, text

    async def _prompt(self, prompt: str, limits: RunLimits) -> tuple[str, dict[str, int]]:
        return await ask_pi(self.config, prompt, limits)

    def _plan_prompt(self, request: ResearchRequest) -> str:
        index = [f"{item.work}/{item.volume}={item.version_id}" for item in request.materials]
        return (
            "你是历史研究助手。研究问题："
            + request.question
            + "\n可用材料："
            + "；".join(index)
            + "\n请给出用于检索原文的检索词与反证检索词，只输出 JSON，不要解释，不要使用工具：\n"
            '{"queries":["..."],"counter_queries":["..."]}'
        )

    def _claims_prompt(self, request: ResearchRequest, passages: list[dict[str, object]]) -> str:
        lines = [
            "研究问题：" + request.question,
            "以下是检索命中的原文片段（JSON，start/end 是整卷字符坐标）：",
            json.dumps({"passages": passages}, ensure_ascii=False),
            "请只依据这些片段写出 1-3 条论断（每条 1-2 条引文），优先采用包含多个检索词、"
            "直接记载于謙行事的片段；片段确实不支持任何论断时才返回空列表。"
            "只输出 JSON，不要解释、不要复述片段、不要输出推理过程：",
            '{"claims":[{"statement":"...","citations":[{"version_id":"...","start":0,"end":20,'
            '"exact_quote":"..."}]}]}',
            "引文必须从某个片段的 text 中逐字截取（8-60 字），start/end 用整卷坐标"
            "（= 片段 start + 片段内起止偏移）；exact_quote 必须与该段逐字一致；"
            "只证明关键词出现的短词不能作为引文；不得改写、不得杜撰、不得跨版本引用。",
        ]
        if request.feedback:
            lines.append("上一次校验失败原因（必须修正）：" + "；".join(request.feedback))
        return "\n".join(lines)

    def _counter_prompt(self, claims: dict[str, object], passages: list[dict[str, object]]) -> str:
        statements = [
            str(item.get("statement"))
            for item in _object_list(claims.get("claims"))
            if item.get("statement")
        ]
        return "\n".join(
            [
                "待检验的论断：" + "；".join(statements),
                "以下是为寻找反证而检索到的原文片段（JSON，start/end 是整卷坐标）：",
                json.dumps({"passages": passages}, ensure_ascii=False),
                "请指出这些片段中是否存在与上述论断相反或不同的记载，最多 5 条结论，"
                "只输出 JSON，不要解释、不要输出推理过程：",
                '{"findings":["..."]}',
                "若没有找到，如实写：未找到反证（不等于不存在）。",
            ]
        )


@dataclass
class _Hit:
    """一次逐字命中的位置与它覆盖到的检索词。"""

    version_id: str
    start: int
    end: int
    terms: set[str]


@dataclass
class _Window:
    """归并后的候选片段窗口。"""

    version_id: str
    start: int
    end: int
    terms: set[str]


def _search(
    tools: BudgetedTools, queries: list[str], *, max_calls: int = SNIPPET_LIMIT
) -> list[_Hit]:
    """逐字检索；命中记录其覆盖到的检索词，供后续按相关度挑选片段。"""
    seen: dict[tuple[str, int, int], _Hit] = {}
    for query in queries[:SNIPPET_LIMIT]:
        for term in _terms(query):
            if tools.calls >= max_calls:
                return list(seen.values())
            for hit in tools.search(term, limit=HITS_PER_QUERY):
                key = (str(hit["version_id"]), as_int(hit["start"]), as_int(hit["end"]))
                entry = seen.setdefault(key, _Hit(*key, terms=set()))
                entry.terms.add(term)
    return list(seen.values())


def _passages(
    tools: BudgetedTools,
    hits: list[_Hit],
    materials: tuple[Material, ...],
    *,
    max_calls: int,
) -> list[dict[str, object]]:
    """把命中归并成原文片段（含整卷坐标），按覆盖到的检索词数排序后取前若干段。"""
    texts = {material.version_id: material.text for material in materials}
    windows = _windows(hits, texts)
    ranked = sorted(windows.values(), key=lambda w: (-len(w.terms), w.version_id, w.start))
    passages: list[dict[str, object]] = []
    for window in ranked:
        if tools.calls >= max_calls or len(passages) >= PASSAGE_LIMIT:
            break
        start, end = _sentence_bounds(texts[window.version_id], window.start, window.end)
        if start >= end:
            continue
        payload = tools.read(window.version_id, start, end)
        passages.append(
            {
                "version_id": window.version_id,
                "start": start,
                "end": end,
                "text": payload["text"],
            }
        )
    return passages


def _windows(hits: list[_Hit], texts: dict[str, str]) -> dict[tuple[str, int], _Window]:
    """把命中按窗口归并；窗口起点相同即视为同一段，并累计覆盖的检索词。"""
    windows: dict[tuple[str, int], _Window] = {}
    for hit in hits:
        if hit.version_id not in texts:
            continue
        key = (hit.version_id, max(0, hit.start - WINDOW_CHARS))
        entry = windows.setdefault(key, _Window(hit.version_id, key[1], hit.end, set()))
        entry.end = max(entry.end, hit.end)
        entry.terms.update(hit.terms)
    return windows


def _sentence_bounds(text: str, start: int, end: int) -> tuple[int, int]:
    """把窗口扩到句子边界，让模型看到完整记载而不是断句片段。"""
    head = max(0, start - SENTENCE_CHARS)
    tail = min(len(text), end + SENTENCE_CHARS)
    for mark in _SENTENCE_END:
        cut = text.rfind(mark, head, start)
        if cut != -1:
            start = cut + 1
            break
    for mark in _SENTENCE_END:
        cut = text.find(mark, end, tail)
        if cut != -1:
            end = cut + 1
            break
    return start, min(end, len(text))


def _terms(query: str) -> list[str]:
    """把检索词拆成可逐字匹配的短词。

    模型有时给的是带空格的组合词；组合里的一两个字（如「戰」「年」）会带回大量无关命中，
    因此组合查询只保留 2 字以上的词；本身就是单个短词时原样使用。
    """
    parts = [part for part in query.split() if part]
    if len(parts) <= 1:
        return [query] if 1 <= len(query) <= 12 else []
    return [part for part in parts if 2 <= len(part) <= 12]


def _object_list(value: object) -> list[dict[str, object]]:
    """把 JSON 里的数组安全窄化成对象列表；非数组/非对象一律忽略。"""
    if not isinstance(value, list):
        return []
    return [
        cast("dict[str, object]", item)
        for item in cast("list[object]", value)
        if isinstance(item, dict)
    ]


def _string_list(value: object) -> list[str]:
    if not isinstance(value, list):
        return []
    return [item for item in cast("list[object]", value) if isinstance(item, str) and item.strip()]


def parse_claims(payload: dict[str, object]) -> tuple[ClaimDraft, ...]:
    claims: list[ClaimDraft] = []
    for item in _object_list(payload.get("claims")):
        statement = item.get("statement")
        citations = _citations(item.get("citations"))
        if isinstance(statement, str) and citations:
            claims.append(ClaimDraft(statement=statement, citations=citations))
    return tuple(claims)


def _citations(raw: object) -> tuple[CitationDraft, ...]:
    drafts: list[CitationDraft] = []
    for item in _object_list(raw):
        version_id, quote = item.get("version_id"), item.get("exact_quote")
        start, end = item.get("start"), item.get("end")
        if not isinstance(version_id, str) or not isinstance(quote, str):
            continue
        if not isinstance(start, int) or not isinstance(end, int):
            continue
        drafts.append(CitationDraft(version_id=version_id, start=start, end=end, exact_quote=quote))
    return tuple(drafts)
