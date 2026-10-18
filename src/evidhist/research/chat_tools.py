"""对话内的工具（对话功能方案第 5 节）。

四件事，边界写死：引文只做程序硬校验（不做模糊匹配）；题录入库只存题录字段并把
来源库、许可与检索时间写进出处；报告起草复用既有渲染并如实标记未通过的论断；
评审委托失败时记录失败，不当作通过。
"""

from __future__ import annotations

from collections.abc import Sequence

from sqlalchemy.ext.asyncio import AsyncSession

from evidhist.research.citations import (
    CitationDraft,
    CitationVerdict,
    ClaimDraft,
    verify_claim,
)
from evidhist.research.executor import ExecutorError, RunLimitExceeded, RunLimits
from evidhist.research.papers import PaperClient, PaperFetchError, PaperRecord, search_papers
from evidhist.research.review import PiReviewer, Reviewer, ReviewResult, failed_review
from evidhist.research.tools import Material, ReadOnlyTools, ToolError
from evidhist.sources_service import NewSource, create_source

PAPER_AUTHOR_LIMIT = 6
USAGE_TERMS_LIMIT = 500


def verify_citation(
    materials: Sequence[Material],
    *,
    version_id: str,
    start: int,
    end: int,
    exact_quote: str,
) -> dict[str, object]:
    """单条引文的程序硬校验；返回可直接写入事件与界面的载荷。"""
    draft = CitationDraft(version_id=version_id, start=start, end=end, exact_quote=exact_quote)
    verdict = verify_claim(materials, ClaimDraft(statement="", citations=(draft,)))
    citation = verdict.citations[0] if verdict.citations else None
    return {
        "ok": verdict.ok,
        "code": verdict.code if citation is None else citation.code,
        "version_id": version_id,
        "start": start,
        "end": end,
        "exact_quote": exact_quote,
    }


def paper_record_text(record: PaperRecord) -> str:
    """题录正文：只有书目字段，不包含全文或摘要。"""
    lines = [f"题录：{record.title}"]
    if record.authors:
        shown = record.authors[:PAPER_AUTHOR_LIMIT]
        suffix = "等" if len(record.authors) > PAPER_AUTHOR_LIMIT else ""
        lines.append("作者：" + "、".join(shown) + suffix)
    if record.year is not None:
        lines.append(f"年份：{record.year}")
    if record.venue:
        lines.append(f"发表处：{record.venue}")
    if record.doi:
        lines.append(f"DOI：{record.doi}")
    lines.append(f"链接：{record.url}")
    lines.append("来源库：" + "、".join(record.sources))
    lines.append(f"检索时间：{record.retrieved_at.isoformat()}")
    return "\n".join(lines)


def paper_origin(record: PaperRecord) -> str:
    """出处：来源库 + 链接 + 检索时间，便于复核这条题录从哪里来。"""
    sources = "、".join(record.sources)
    return f"{sources} 题录检索（{record.url}，检索于 {record.retrieved_at.isoformat()}）"


def paper_usage_terms(record: PaperRecord) -> str:
    """许可说明：按来源库分别写清；题录不是史料正文，不能当作引文证据。"""
    parts = [f"来源库：{'、'.join(record.sources)}"]
    if "openalex" in record.sources:
        parts.append("OpenAlex 元数据按 CC0 提供")
    if "crossref" in record.sources:
        parts.append("Crossref 题录按其开放条款转载")
    parts.append("仅题录（书目字段），未收录全文，不得作为史料引文证据")
    terms = "；".join(parts)
    return terms[:USAGE_TERMS_LIMIT]


async def import_paper_record(session: AsyncSession, record: PaperRecord) -> dict[str, object]:
    """把题录写入材料库；同一题录重复导入命中既有来源（内容与出处都是确定的）。"""
    text = paper_record_text(record)
    source, version, created = await create_source(
        session,
        NewSource(
            title=record.title,
            origin=paper_origin(record),
            usage_terms=paper_usage_terms(record),
            text=text,
            label=(f"题录·{record.year}" if record.year is not None else "题录"),
        ),
    )
    return {
        "ok": True,
        "source_id": str(source.id),
        "version_id": str(version.id),
        "created": created,
    }


def reviewer_model(reviewer: object) -> str:
    """评审器对应的模型名；用于失败记录，避免把未知模型写成某个具体模型。"""
    if isinstance(reviewer, PiReviewer):
        return reviewer.config.model
    return str(getattr(reviewer, "model_name", getattr(reviewer, "model", "unknown")))


async def request_review(reviewer: Reviewer, report_text: str, limits: RunLimits) -> ReviewResult:
    """委托评审；超时、协议错误与格式不符都记录为失败。"""
    try:
        return await reviewer.review(report_text, limits)
    except (RunLimitExceeded, ExecutorError) as error:
        return failed_review(reviewer_model(reviewer), f"review_{error.reason}")
    except Exception as error:  # 评审失败不能中断对话，也不能记为通过
        return failed_review(reviewer_model(reviewer), f"review_error_{type(error).__name__}")


__all__ = [
    "CitationVerdict",
    "SessionToolbox",
    "import_paper_record",
    "paper_origin",
    "paper_record_text",
    "paper_usage_terms",
    "request_review",
    "reviewer_model",
    "verify_citation",
]


class SessionToolbox:
    """把只读材料工具、外部题录检索与题录入库接到一个数据库会话上。

    不认识的工具、非法参数与工具自身错误都返回 `ok=false` 与原因码，不抛异常：
    对话循环据此继续，而不是整轮失败。
    """

    def __init__(
        self,
        session: AsyncSession,
        *,
        materials: Sequence[Material],
        tools: ReadOnlyTools,
        client: PaperClient,
    ) -> None:
        self.session = session
        self.materials = materials
        self.tools = tools
        self.client = client
        self.last_papers: tuple[PaperRecord, ...] = ()

    async def call(self, name: str, arguments: dict[str, object]) -> dict[str, object]:
        handlers = {
            "list_materials": self._list_materials,
            "search": self._search,
            "read": self._read,
            "exact_quote": self._exact_quote,
            "verify_citation": self._verify,
            "search_papers": self._search_papers,
            "import_paper_record": self._import_paper,
        }
        handler = handlers.get(name)
        if handler is None:
            return {"ok": False, "code": "unknown_tool", "tool": name}
        try:
            return await handler(arguments)
        except (ToolError, PaperFetchError) as error:
            return {"ok": False, "code": str(error)}

    async def _list_materials(self, _arguments: dict[str, object]) -> dict[str, object]:
        return {"ok": True, "materials": self.tools.list_materials()}

    async def _search(self, arguments: dict[str, object]) -> dict[str, object]:
        query = arguments.get("query")
        if not isinstance(query, str):
            raise ToolError("empty_query")
        limit = arguments.get("limit")
        hits = self.tools.search(query, limit=limit if isinstance(limit, int) else 5)
        labels = {
            material.version_id: (material.work, material.volume) for material in self.materials
        }
        return {
            "ok": True,
            "hits": [
                {
                    **hit,
                    "work": labels.get(str(hit["version_id"]), ("", ""))[0],
                    "volume": labels.get(str(hit["version_id"]), ("", ""))[1],
                }
                for hit in hits
            ],
        }

    async def _read(self, arguments: dict[str, object]) -> dict[str, object]:
        return {"ok": True, **self.tools.read(*_range_args(arguments))}

    async def _exact_quote(self, arguments: dict[str, object]) -> dict[str, object]:
        quote = self.tools.exact_quote(*_range_args(arguments))
        return {"ok": True, "exact_quote": quote}

    async def _verify(self, arguments: dict[str, object]) -> dict[str, object]:
        quote = arguments.get("exact_quote")
        version_id, start, end = _range_args(arguments)
        return verify_citation(
            self.materials,
            version_id=version_id,
            start=start,
            end=end,
            exact_quote=quote if isinstance(quote, str) else "",
        )

    async def _search_papers(self, arguments: dict[str, object]) -> dict[str, object]:
        query = arguments.get("query")
        if not isinstance(query, str) or not query.strip():
            return {"ok": False, "code": "empty_query"}
        result = await search_papers(query, client=self.client)
        self.last_papers = result.records
        return {
            "ok": True,
            "errors": list(result.errors),
            "records": [
                {
                    "index": index,
                    "sources": list(record.sources),
                    "title": record.title,
                    "authors": list(record.authors),
                    "year": record.year,
                    "venue": record.venue,
                    "doi": record.doi,
                    "url": record.url,
                }
                for index, record in enumerate(result.records)
            ],
        }

    async def _import_paper(self, arguments: dict[str, object]) -> dict[str, object]:
        index = arguments.get("index")
        if not isinstance(index, int) or not 0 <= index < len(self.last_papers):
            return {"ok": False, "code": "paper_index_out_of_range"}
        outcome = await import_paper_record(self.session, self.last_papers[index])
        return {**outcome, "code": None}


def _range_args(arguments: dict[str, object]) -> tuple[str, int, int]:
    """取 version_id/start/end；缺字段或类型不符按非法区间处理。"""
    version_id, start, end = (
        arguments.get("version_id"),
        arguments.get("start"),
        arguments.get("end"),
    )
    if not isinstance(version_id, str) or not isinstance(start, int) or not isinstance(end, int):
        raise ToolError("invalid_range")
    return version_id, start, end
