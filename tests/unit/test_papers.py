"""外部论文题录检索（OpenAlex + Crossref）的单元测试，不联网。

对应[对话功能方案](../docs/chat-feature-plan-2026-10-18.md)第 6 节：只取题录字段；
两个来源按 DOI 去重合并；单一来源失败不影响另一来源的结果，但必须如实记录。
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

import pytest

from evidhist.research.papers import (
    PaperFetchError,
    PaperRecord,
    merge_records,
    parse_crossref,
    parse_openalex,
    search_papers,
)

RETRIEVED = datetime(2026, 10, 18, 12, 0, tzinfo=UTC)

OPENALEX_PAYLOAD: dict[str, Any] = {
    "results": [
        {
            "id": "https://openalex.org/W1",
            "doi": "https://doi.org/10.2307/1234",
            "title": "The Defense of Beijing in 1449",
            "publication_year": 1998,
            "authorships": [
                {"author": {"display_name": "Li Jiajin"}},
                {"author": {"display_name": "Wang Ming"}},
            ],
            "primary_location": {"source": {"display_name": "Ming Studies"}},
        },
        {
            "id": "https://openalex.org/W2",
            "doi": None,
            "title": "土木之變與京師守禦",
            "publication_year": 2005,
            "authorships": [],
            "primary_location": None,
        },
    ]
}

CROSSREF_PAYLOAD: dict[str, Any] = {
    "message": {
        "items": [
            {
                "DOI": "10.2307/1234",
                "title": ["The Defense of Beijing in 1449"],
                "author": [{"given": "Jiajin", "family": "Li"}],
                "issued": {"date-parts": [[1998]]},
                "container-title": ["Ming Studies"],
                "URL": "https://doi.org/10.2307/1234",
            },
            {
                "DOI": "10.1017/S0001",
                "title": ["Yu Qian and the Tumu Crisis"],
                "author": [{"given": "Mei", "family": "Chen"}],
                "issued": {"date-parts": [[2011]]},
                "container-title": ["Journal of Chinese History"],
                "URL": "https://doi.org/10.1017/S0001",
            },
        ]
    }
}


def test_openalex_records_are_normalised() -> None:
    records = parse_openalex(OPENALEX_PAYLOAD, retrieved_at=RETRIEVED)

    assert len(records) == 2
    first = records[0]
    assert first.title == "The Defense of Beijing in 1449"
    assert first.authors == ("Li Jiajin", "Wang Ming")
    assert first.year == 1998
    assert first.venue == "Ming Studies"
    assert first.doi == "10.2307/1234"
    assert first.url == "https://doi.org/10.2307/1234"
    assert first.sources == ("openalex",)
    assert first.retrieved_at == RETRIEVED

    without_doi = records[1]
    assert without_doi.doi is None
    assert without_doi.url == "https://openalex.org/W2"
    assert without_doi.authors == ()


def test_crossref_records_are_normalised() -> None:
    records = parse_crossref(CROSSREF_PAYLOAD, retrieved_at=RETRIEVED)

    assert [record.doi for record in records] == ["10.2307/1234", "10.1017/S0001"]
    first = records[0]
    assert first.authors == ("Jiajin Li",)  # Crossref 的 given/family 字段顺序
    assert first.year == 1998
    assert first.venue == "Ming Studies"
    assert first.sources == ("crossref",)


@pytest.mark.parametrize(
    "payload",
    [{}, {"results": "nope"}, {"results": [{"title": ""}]}, {"results": ["x"]}],
)
def test_openalex_tolerates_malformed_items(payload: dict[str, Any]) -> None:
    records = parse_openalex(payload, retrieved_at=RETRIEVED)
    assert all(record.title for record in records)


def test_malformed_crossref_payloads_yield_no_records() -> None:
    assert parse_crossref({}, retrieved_at=RETRIEVED) == []
    assert parse_crossref({"message": {"items": "nope"}}, retrieved_at=RETRIEVED) == []
    assert parse_crossref({"message": {"items": [{"DOI": "10.1/x"}]}}, retrieved_at=RETRIEVED) == []


def test_records_with_the_same_doi_merge_and_keep_both_sources() -> None:
    merged = merge_records(
        parse_openalex(OPENALEX_PAYLOAD, retrieved_at=RETRIEVED)
        + parse_crossref(CROSSREF_PAYLOAD, retrieved_at=RETRIEVED)
    )

    dois = [record.doi for record in merged]
    assert dois.count("10.2307/1234") == 1
    shared = next(record for record in merged if record.doi == "10.2307/1234")
    assert shared.sources == ("openalex", "crossref")


class FakeResponse:
    def __init__(self, status_code: int, payload: dict[str, Any] | None) -> None:
        self.status_code = status_code
        self._payload = payload

    def json(self) -> dict[str, Any]:
        if self._payload is None:
            raise ValueError("not json")
        return self._payload


class FakeClient:
    """记录请求并按键返回响应，用来固定 URL、参数与 UA。"""

    def __init__(self, responses: dict[str, Any]) -> None:
        self.responses = responses
        self.calls: list[tuple[str, dict[str, Any], dict[str, str]]] = []

    async def get(self, url: str, **kwargs: Any) -> Any:
        self.calls.append((url, kwargs.get("params") or {}, kwargs.get("headers") or {}))
        result = self.responses[url]
        if isinstance(result, Exception):
            raise result
        return result


async def test_search_queries_both_sources_and_merges_them() -> None:
    client = FakeClient(
        {
            "https://api.openalex.org/works": FakeResponse(200, OPENALEX_PAYLOAD),
            "https://api.crossref.org/works": FakeResponse(200, CROSSREF_PAYLOAD),
        }
    )

    result = await search_papers("Tumu crisis", client=client, retrieved_at=RETRIEVED)

    assert result.errors == ()
    assert len(result.records) == 3  # 两个来源共 4 条，其中 1 条 DOI 相同合并
    assert {call[0] for call in client.calls} == {
        "https://api.openalex.org/works",
        "https://api.crossref.org/works",
    }
    openalex_params = next(call[1] for call in client.calls if "openalex" in call[0])
    crossref_params = next(call[1] for call in client.calls if "crossref" in call[0])
    assert openalex_params == {"search": "Tumu crisis", "per-page": 5}
    assert crossref_params == {"query.bibliographic": "Tumu crisis", "rows": 5}
    assert all("EvidHist" in headers["User-Agent"] for _url, _params, headers in client.calls)


async def test_a_failed_source_is_reported_without_losing_the_other() -> None:
    client = FakeClient(
        {
            "https://api.openalex.org/works": FakeResponse(200, OPENALEX_PAYLOAD),
            "https://api.crossref.org/works": FakeResponse(500, None),
        }
    )

    result = await search_papers("Tumu crisis", client=client, retrieved_at=RETRIEVED)

    assert len(result.records) == 2
    assert result.errors == ("crossref:500",)


async def test_network_errors_are_reported_as_source_errors() -> None:
    client = FakeClient(
        {
            "https://api.openalex.org/works": PaperFetchError("openalex", "timeout"),
            "https://api.crossref.org/works": FakeResponse(200, CROSSREF_PAYLOAD),
        }
    )

    result = await search_papers("Tumu crisis", client=client, retrieved_at=RETRIEVED)

    assert len(result.records) == 2
    assert result.errors == ("openalex:timeout",)


def test_records_without_doi_merge_by_normalised_title() -> None:
    left = PaperRecord(
        sources=("openalex",),
        title="土木之變與京師守禦",
        authors=(),
        year=2005,
        venue="",
        doi=None,
        url="https://openalex.org/W2",
        retrieved_at=RETRIEVED,
    )
    right = PaperRecord(
        sources=("crossref",),
        title="土木之變與京師守禦 ",
        authors=("王明",),
        year=2005,
        venue="史學集刊",
        doi=None,
        url="https://crossref.example/x",
        retrieved_at=RETRIEVED,
    )

    merged = merge_records([left, right])

    assert len(merged) == 1
    assert merged[0].sources == ("openalex", "crossref")
    assert merged[0].authors == ("王明",)


async def test_invalid_json_is_reported_as_a_source_error() -> None:
    client = FakeClient(
        {
            "https://api.openalex.org/works": FakeResponse(200, None),
            "https://api.crossref.org/works": FakeResponse(200, CROSSREF_PAYLOAD),
        }
    )

    result = await search_papers("Tumu crisis", client=client, retrieved_at=RETRIEVED)

    assert result.errors == ("openalex:invalid_json",)
    assert len(result.records) == 2


async def test_transport_errors_are_reported_not_raised() -> None:
    import httpx2

    client = FakeClient(
        {
            "https://api.openalex.org/works": httpx2.ConnectError("boom"),
            "https://api.crossref.org/works": FakeResponse(200, CROSSREF_PAYLOAD),
        }
    )

    result = await search_papers("Tumu crisis", client=client, retrieved_at=RETRIEVED)

    assert result.errors == ("openalex:ConnectError",)
    assert len(result.records) == 2


def test_crossref_items_without_optional_fields_are_tolerated() -> None:
    payload = {"message": {"items": [{"DOI": "10.1/x", "title": ["仅标题"]}]}}

    records = parse_crossref(payload, retrieved_at=RETRIEVED)

    assert len(records) == 1
    assert records[0].authors == ()
    assert records[0].year is None
    assert records[0].venue == ""
