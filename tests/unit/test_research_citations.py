"""引用硬校验的行为与属性测试（离线）。

对应[首版最小技术方案](../docs/minimal-technical-plan-2026-10-18.md)§4.2/§5：
论断的每条引文必须在入库版本里逐字命中；失败给出稳定原因码，且不被任何模型评分覆盖。
"""

from __future__ import annotations

from hypothesis import given, settings
from hypothesis import strategies as st

from evidhist.research.citations import (
    CitationDraft,
    ClaimDraft,
    verify_claim,
    verify_claims,
)
from evidhist.research.tools import Material

MATERIALS = (
    Material(version_id="v-170", work="明史", volume="卷170", text="于謙字廷益，錢塘人。"),
    Material(version_id="v-032", work="明史紀事本末", volume="卷32", text="土木之變，京師震恐。"),
)


def test_verbatim_citation_passes() -> None:
    verdict = verify_claim(
        MATERIALS,
        ClaimDraft(statement="于謙為錢塘人", citations=(CitationDraft("v-170", 6, 9, "錢塘人"),)),
    )
    assert verdict.ok is True
    assert verdict.citations[0].ok is True
    assert verdict.citations[0].code is None


def test_tampered_quote_is_rejected_even_when_offsets_exist() -> None:
    verdict = verify_claim(
        MATERIALS,
        ClaimDraft(statement="改寫過的引文", citations=(CitationDraft("v-170", 6, 9, "錢塘縣"),)),
    )
    assert verdict.ok is False
    assert verdict.code == "citation_failed"
    assert verdict.citations[0].code == "quote_mismatch"


def test_out_of_range_and_unknown_version_are_distinguished() -> None:
    out_of_range = verify_claim(
        MATERIALS,
        ClaimDraft(statement="越界", citations=(CitationDraft("v-170", 3, 999, "錢塘人"),)),
    )
    assert out_of_range.citations[0].code == "invalid_range"
    unknown = verify_claim(
        MATERIALS, ClaimDraft(statement="不存在版本", citations=(CitationDraft("v-x", 0, 1, "于"),))
    )
    assert unknown.citations[0].code == "unknown_version"


def test_claim_without_citation_is_not_ok() -> None:
    verdict = verify_claim(MATERIALS, ClaimDraft(statement="沒有引文的斷言", citations=()))
    assert verdict.ok is False
    assert verdict.code == "no_citation"


def test_every_citation_is_reported_in_order() -> None:
    verdicts = verify_claims(
        MATERIALS,
        (
            ClaimDraft(
                statement="混合引文",
                citations=(
                    CitationDraft("v-170", 0, 2, "于謙"),
                    CitationDraft("v-032", 0, 4, "土木之變"),
                ),
            ),
            ClaimDraft(statement="錯誤引文", citations=(CitationDraft("v-032", 0, 4, "土木之变"),)),
        ),
    )
    assert [verdict.ok for verdict in verdicts] == [True, False]
    assert [item.ok for item in verdicts[0].citations] == [True, True]
    assert [item.code for item in verdicts[1].citations] == ["quote_mismatch"]


@given(
    text=st.text(alphabet="于謙土木之變京師震恐", min_size=2, max_size=40),
    data=st.data(),
)
@settings(max_examples=200, deadline=None)
def test_property_exact_slice_passes_and_any_changed_character_fails(
    text: str, data: st.DataObject
) -> None:
    start = data.draw(st.integers(min_value=0, max_value=len(text) - 1))
    end = data.draw(st.integers(min_value=start + 1, max_value=len(text)))
    quote = text[start:end]
    materials = (Material(version_id="v", work="W", volume="卷1", text=text),)

    assert verify_claim(
        materials, ClaimDraft(statement="s", citations=(CitationDraft("v", start, end, quote),))
    ).ok

    replacement = "甲" if quote[0] != "甲" else "乙"
    tampered = replacement + quote[1:]
    verdict = verify_claim(
        materials, ClaimDraft(statement="s", citations=(CitationDraft("v", start, end, tampered),))
    )
    assert verdict.ok is False
    assert verdict.citations[0].code == "quote_mismatch"


def test_verification_rejects_a_claim_that_cites_a_different_version_text() -> None:
    """同一段文字若不在所引版本里，必须拒绝（版本绑定，不做跨版本兜底）。"""
    verdict = verify_claim(
        MATERIALS,
        ClaimDraft(statement="s", citations=(CitationDraft("v-032", 0, 2, "于謙"),)),
    )
    assert verdict.ok is False
    assert verdict.citations[0].code == "quote_mismatch"
