"""只读资料工具的行为测试（离线，不连数据库）。

对应[首版最小技术方案](../docs/minimal-technical-plan-2026-10-18.md)§4.3 与 M07：
工具只能读已入库材料，返回可回查的位置（version_id + 区间），不提供写入、文件、网络或 shell。
"""

from __future__ import annotations

from hashlib import sha256

import pytest

from evidhist.research.tools import Material, ReadOnlyTools, ToolError

MATERIALS = (
    Material(
        version_id="v-170",
        work="明史",
        volume="卷170",
        text="于謙字廷益，錢塘人。于謙死，天下冤之。",
    ),
    Material(version_id="v-032", work="明史紀事本末", volume="卷32", text="土木之變，京師震恐。"),
)


def tools() -> ReadOnlyTools:
    return ReadOnlyTools(MATERIALS)


def test_exposes_only_read_only_tools() -> None:
    public = {name for name in dir(tools()) if not name.startswith("_")}
    assert public == {"list_materials", "search", "read", "exact_quote"}


def test_list_materials_reports_locators_without_returning_full_text() -> None:
    listed = tools().list_materials()
    assert [item["version_id"] for item in listed] == ["v-032", "v-170"]
    assert listed[1]["work"] == "明史"
    assert listed[1]["volume"] == "卷170"
    assert listed[1]["chars"] == len(MATERIALS[0].text)
    assert "text" not in listed[1]


def test_search_returns_every_occurrence_with_offsets_and_context() -> None:
    hits = tools().search("于謙")
    assert [(hit["version_id"], hit["start"], hit["end"]) for hit in hits] == [
        ("v-170", 0, 2),
        ("v-170", 10, 12),
    ]
    assert all(hit["quote"] == "于謙" for hit in hits)
    assert "text" not in hits[0]


def test_search_respects_version_filter_and_limit() -> None:
    assert tools().search("于謙", version_ids=["v-032"]) == []
    assert len(tools().search("于謙", limit=1)) == 1


def test_search_rejects_empty_query_and_unknown_version() -> None:
    with pytest.raises(ToolError) as empty:
        tools().search("   ")
    assert empty.value.code == "empty_query"
    with pytest.raises(ToolError) as unknown:
        tools().search("于謙", version_ids=["v-missing"])
    assert unknown.value.code == "unknown_version"
    with pytest.raises(ToolError) as limit:
        tools().search("于謙", limit=0)
    assert limit.value.code == "invalid_limit"


def test_read_returns_exact_slice_and_version_digest() -> None:
    payload = tools().read("v-170", 0, 2)
    assert payload["text"] == "于謙"
    assert payload["version_sha256"] == sha256(MATERIALS[0].text.encode("utf-8")).hexdigest()
    assert payload["start"] == 0 and payload["end"] == 2


def test_read_and_exact_quote_reject_invalid_ranges_and_versions() -> None:
    for call in (
        lambda: tools().read("v-170", -1, 2),
        lambda: tools().read("v-170", 3, 3),
        lambda: tools().read("v-170", 0, 10_000),
    ):
        with pytest.raises(ToolError) as error:
            call()
        assert error.value.code == "invalid_range"
    with pytest.raises(ToolError) as unknown:
        tools().exact_quote("v-missing", 0, 1)
    assert unknown.value.code == "unknown_version"


def test_exact_quote_matches_the_stored_text_verbatim() -> None:
    assert tools().exact_quote("v-032", 0, 4) == "土木之變"
