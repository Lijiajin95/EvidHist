"""外部论文题录检索：OpenAlex 与 Crossref（对话功能方案第 6 节）。

只取题录字段（标题、作者、年份、发表处、DOI/链接），两个来源分别检索后按 DOI
合并；单一来源失败如实记入 `errors`，不掩盖另一来源的结果。不抓取全文、不下载
附件，TLS 校验保持默认开启。
"""

from __future__ import annotations

import json
from collections.abc import Iterable
from dataclasses import dataclass, replace
from datetime import UTC, datetime
from typing import Any, Protocol, cast

import httpx2

OPENALEX_URL = "https://api.openalex.org/works"
CROSSREF_URL = "https://api.crossref.org/works"
USER_AGENT = "EvidHist/0.1 (paper metadata search; https://github.com/Lijiajin95/EvidHist)"
TIMEOUT_SECONDS = 10.0
DEFAULT_LIMIT = 5


class PaperResponse(Protocol):
    """检索需要的最小响应能力；`httpx2.Response` 与测试替身都满足。"""

    status_code: int

    def json(self) -> Any: ...


class PaperClient(Protocol):
    """检索需要的最小客户端能力；`httpx2.AsyncClient` 与测试替身都满足。"""

    async def get(
        self,
        url: str,
        *,
        params: dict[str, str | int],
        headers: dict[str, str],
        timeout: float,
    ) -> PaperResponse: ...


class PaperFetchError(RuntimeError):
    """某个来源的检索失败；`reason` 用于在界面上如实标注。"""

    def __init__(self, source: str, reason: str) -> None:
        self.source = source
        self.reason = reason
        super().__init__(f"{source}: {reason}")


@dataclass(frozen=True)
class PaperRecord:
    """一条题录；`sources` 记录它出现在哪些来源库（去重后可能是多个）。"""

    sources: tuple[str, ...]
    title: str
    authors: tuple[str, ...]
    year: int | None
    venue: str
    doi: str | None
    url: str
    retrieved_at: datetime


@dataclass(frozen=True)
class PaperSearchResult:
    records: tuple[PaperRecord, ...]
    errors: tuple[str, ...]


def _text(value: object) -> str:
    return value.strip() if isinstance(value, str) else ""


def _year(value: object) -> int | None:
    return value if isinstance(value, int) and 1000 <= value <= 2200 else None


def _doi(value: object) -> str | None:
    raw = _text(value)
    for prefix in ("https://doi.org/", "http://doi.org/", "doi:"):
        if raw.lower().startswith(prefix):
            raw = raw[len(prefix) :]
    return raw or None


def _drop_empty(records: Iterable[PaperRecord]) -> list[PaperRecord]:
    return [record for record in records if record.title]


def _openalex_authors(entry: dict[str, object]) -> tuple[str, ...]:
    raw = entry.get("authorships")
    if not isinstance(raw, list):
        return ()
    authors: list[str] = []
    for raw_authorship in cast("list[object]", raw):
        if not isinstance(raw_authorship, dict):
            continue
        author = cast("dict[str, object]", raw_authorship).get("author")
        if isinstance(author, dict):
            name = _text(cast("dict[str, object]", author).get("display_name"))
            if name:
                authors.append(name)
    return tuple(authors)


def _openalex_venue(entry: dict[str, object]) -> str:
    location = entry.get("primary_location")
    if not isinstance(location, dict):
        return ""
    source = cast("dict[str, object]", location).get("source")
    if not isinstance(source, dict):
        return ""
    return _text(cast("dict[str, object]", source).get("display_name"))


def parse_openalex(payload: dict[str, Any], *, retrieved_at: datetime) -> list[PaperRecord]:
    """解析 OpenAlex `/works` 响应；标题为空或结构不符的条目忽略。"""
    raw = payload.get("results")
    if not isinstance(raw, list):
        return []
    records: list[PaperRecord] = []
    for raw_item in cast("list[object]", raw):
        if not isinstance(raw_item, dict):
            continue
        entry = cast("dict[str, object]", raw_item)
        title = _text(entry.get("title"))
        if not title:
            continue
        authors = _openalex_authors(entry)
        venue = _openalex_venue(entry)
        doi = _doi(entry.get("doi"))
        url = f"https://doi.org/{doi}" if doi else _text(entry.get("id"))
        records.append(
            PaperRecord(
                sources=("openalex",),
                title=title,
                authors=authors,
                year=_year(entry.get("publication_year")),
                venue=venue,
                doi=doi,
                url=url,
                retrieved_at=retrieved_at,
            )
        )
    return _drop_empty(records)


def _crossref_year(issued: object) -> int | None:
    if not isinstance(issued, dict):
        return None
    parts = cast("dict[str, object]", issued).get("date-parts")
    if not isinstance(parts, list) or not parts:
        return None
    first = cast("list[object]", parts)[0]
    if not isinstance(first, list) or not first:
        return None
    return _year(cast("list[object]", first)[0])


def parse_crossref(payload: dict[str, Any], *, retrieved_at: datetime) -> list[PaperRecord]:
    """解析 Crossref `/works` 响应；同样忽略无标题的条目。"""
    message = payload.get("message")
    items = cast("dict[str, object]", message).get("items") if isinstance(message, dict) else None
    if not isinstance(items, list):
        return []
    records: list[PaperRecord] = []
    for raw_item in cast("list[object]", items):
        if not isinstance(raw_item, dict):
            continue
        entry = cast("dict[str, object]", raw_item)
        titles = entry.get("title")
        title = (
            _text(cast("list[object]", titles)[0]) if isinstance(titles, list) and titles else ""
        )
        if not title:
            continue
        authors: list[str] = []
        raw_author = entry.get("author")
        for author in cast("list[object]", raw_author) if isinstance(raw_author, list) else []:
            if not isinstance(author, dict):
                continue
            fields = cast("dict[str, object]", author)
            name = " ".join(
                part for part in (_text(fields.get("given")), _text(fields.get("family"))) if part
            )
            if name:
                authors.append(name)
        year = _crossref_year(entry.get("issued"))
        containers = entry.get("container-title")
        venue = (
            _text(cast("list[object]", containers)[0])
            if isinstance(containers, list) and containers
            else ""
        )
        doi = _doi(entry.get("DOI"))
        records.append(
            PaperRecord(
                sources=("crossref",),
                title=title,
                authors=tuple(authors),
                year=year,
                venue=venue,
                doi=doi,
                url=_text(entry.get("URL")) or (f"https://doi.org/{doi}" if doi else ""),
                retrieved_at=retrieved_at,
            )
        )
    return _drop_empty(records)


def _key(record: PaperRecord) -> tuple[str, str]:
    if record.doi:
        return ("doi", record.doi.lower())
    return ("title", "".join(record.title.split()).lower())


def merge_records(records: Iterable[PaperRecord]) -> list[PaperRecord]:
    """按 DOI（无 DOI 时按规范化标题）合并；来源标记取并集，空字段由后来的记录补全。"""
    merged: dict[tuple[str, str], PaperRecord] = {}
    for record in records:
        key = _key(record)
        existing = merged.get(key)
        if existing is None:
            merged[key] = record
            continue
        sources = existing.sources + tuple(
            source for source in record.sources if source not in existing.sources
        )
        merged[key] = replace(
            existing,
            sources=sources,
            authors=existing.authors or record.authors,
            year=existing.year or record.year,
            venue=existing.venue or record.venue,
            url=existing.url or record.url,
        )
    return list(merged.values())


async def _fetch(
    client: PaperClient, url: str, params: dict[str, str | int], source: str
) -> dict[str, Any]:
    try:
        response = await client.get(
            url, params=params, headers={"User-Agent": USER_AGENT}, timeout=TIMEOUT_SECONDS
        )
    except httpx2.HTTPError as error:  # 网络/超时/TLS 失败
        raise PaperFetchError(source, type(error).__name__) from error
    if response.status_code != 200:
        raise PaperFetchError(source, str(response.status_code))
    try:
        payload = response.json()
    except (ValueError, json.JSONDecodeError) as error:
        raise PaperFetchError(source, "invalid_json") from error
    if not isinstance(payload, dict):
        raise PaperFetchError(source, "invalid_json")
    return cast("dict[str, Any]", payload)


async def search_papers(
    query: str,
    *,
    client: PaperClient,
    retrieved_at: datetime | None = None,
    limit: int = DEFAULT_LIMIT,
) -> PaperSearchResult:
    """两个来源各查一次，合并去重；失败只记该来源的错误。"""
    moment = retrieved_at or datetime.now(UTC)
    errors: list[str] = []
    records: list[PaperRecord] = []
    jobs = (
        ("openalex", OPENALEX_URL, {"search": query, "per-page": limit}),
        ("crossref", CROSSREF_URL, {"query.bibliographic": query, "rows": limit}),
    )
    for source, url, params in jobs:
        try:
            payload = await _fetch(client, url, params, source)
        except PaperFetchError as error:
            errors.append(f"{error.source}:{error.reason}")
            continue
        parsed = (
            parse_openalex(payload, retrieved_at=moment)
            if source == "openalex"
            else parse_crossref(payload, retrieved_at=moment)
        )
        records.extend(parsed)
    return PaperSearchResult(records=tuple(merge_records(records)), errors=tuple(errors))
