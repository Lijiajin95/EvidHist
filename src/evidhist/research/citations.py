"""引文硬校验：论断的每条引文都必须在入库版本里逐字命中（M04）。

- 复用领域规则 `domain.citations.locate_quote`，不另写一套比较逻辑；
- 失败给出稳定原因码（`version_mismatch`/`invalid_range`/`quote_mismatch`/`unknown_version`）；
- 校验只回答"这句话是否确实出现在该版本的这个位置"，不判断历史真伪。
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

from evidhist.domain.citations import Citation, CitationError, TextVersion, locate_quote
from evidhist.research.tools import Material


@dataclass(frozen=True)
class CitationDraft:
    """执行器给出的引文：版本、区间（Unicode 码点，End 开区间）与逐字原文。"""

    version_id: str
    start: int
    end: int
    exact_quote: str


@dataclass(frozen=True)
class ClaimDraft:
    statement: str
    citations: tuple[CitationDraft, ...]


@dataclass(frozen=True)
class CitationVerdict:
    citation: CitationDraft
    ok: bool
    code: str | None


@dataclass(frozen=True)
class ClaimVerdict:
    statement: str
    ok: bool
    code: str | None
    citations: tuple[CitationVerdict, ...]


def verify_claim(materials: Sequence[Material], claim: ClaimDraft) -> ClaimVerdict:
    """逐条校验引文；没有引文或任一引文失败，该论断即不通过。"""
    if not claim.citations:
        return ClaimVerdict(statement=claim.statement, ok=False, code="no_citation", citations=())

    texts = {material.version_id: material.text for material in materials}
    verdicts = tuple(_verify_citation(texts, citation) for citation in claim.citations)
    ok = all(verdict.ok for verdict in verdicts)
    return ClaimVerdict(
        statement=claim.statement,
        ok=ok,
        code=None if ok else "citation_failed",
        citations=verdicts,
    )


def verify_claims(
    materials: Sequence[Material], claims: Sequence[ClaimDraft]
) -> tuple[ClaimVerdict, ...]:
    return tuple(verify_claim(materials, claim) for claim in claims)


def _verify_citation(texts: dict[str, str], citation: CitationDraft) -> CitationVerdict:
    text = texts.get(citation.version_id)
    if text is None:
        return CitationVerdict(citation=citation, ok=False, code="unknown_version")
    try:
        locate_quote(
            TextVersion(version_id=citation.version_id, text=text),
            Citation(
                version_id=citation.version_id,
                start=citation.start,
                end=citation.end,
                exact_quote=citation.exact_quote,
            ),
        )
    except CitationError as error:
        return CitationVerdict(citation=citation, ok=False, code=error.code)
    return CitationVerdict(citation=citation, ok=True, code=None)
