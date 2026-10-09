"""Claims and evidence bindings with natural-key idempotency.

A claim is a short statement kept unique by its exact text. Evidence binds a
claim to a citation inside a specific immutable text version with a relation
(supports / contradicts / mentions / insufficient) and a note. Binding always
re-validates the citation against the persisted version text before storing;
an exact retry returns the existing row. Different sources citing the same
words stay separate evidence entries — same content never merges provenance.
"""

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from evidhist.domain.citations import Citation, TextVersion, locate_quote
from evidhist.domain.materials import normalize_relation
from evidhist.models import ClaimRow, EvidenceRow, SourceRow, TextVersionRow
from evidhist.store_errors import NotFoundError


@dataclass(frozen=True)
class EvidenceBinding:
    claim_id: UUID
    version_id: UUID
    start: int
    end: int
    relation: str
    note: str
    exact_quote: str


@dataclass(frozen=True)
class ClaimSummary:
    id: UUID
    statement: str
    review_status: str
    evidence_count: int
    created_at: datetime


@dataclass(frozen=True)
class EvidenceEntry:
    id: UUID
    claim_id: UUID
    version_id: UUID
    source_id: UUID
    source_title: str
    source_origin: str
    version_label: str
    start: int
    end: int
    quote: str
    relation: str
    note: str
    created_at: datetime


@dataclass(frozen=True)
class ClaimDetail:
    claim: ClaimRow
    evidence: list[EvidenceEntry]


def _entry_from(entry: EvidenceRow, version: TextVersionRow, source: SourceRow) -> EvidenceEntry:
    return EvidenceEntry(
        id=entry.id,
        claim_id=entry.claim_id,
        version_id=entry.version_id,
        source_id=version.source_id,
        source_title=source.title,
        source_origin=source.origin,
        version_label=version.label,
        start=entry.start,
        end=entry.end,
        quote=version.content[entry.start : entry.end],
        relation=entry.relation,
        note=entry.note,
        created_at=entry.created_at,
    )


async def _evidence_entry(session: AsyncSession, evidence_id: UUID) -> EvidenceEntry:
    row = (
        await session.execute(
            select(EvidenceRow, TextVersionRow, SourceRow)
            .join(TextVersionRow, TextVersionRow.id == EvidenceRow.version_id)
            .join(SourceRow, SourceRow.id == TextVersionRow.source_id)
            .where(EvidenceRow.id == evidence_id)
        )
    ).first()
    if row is None:
        raise NotFoundError("evidence", str(evidence_id))
    return _entry_from(row[0], row[1], row[2])


async def create_claim(session: AsyncSession, statement: str) -> tuple[ClaimRow, bool]:
    existing = (
        await session.execute(select(ClaimRow).where(ClaimRow.statement == statement))
    ).scalar_one_or_none()
    if existing is not None:
        return existing, False
    claim = ClaimRow(id=uuid4(), statement=statement)
    session.add(claim)
    await session.flush()
    return claim, True


async def list_claims(session: AsyncSession) -> list[ClaimSummary]:
    counts = (
        select(EvidenceRow.claim_id, func.count().label("evidence_count"))
        .group_by(EvidenceRow.claim_id)
        .subquery()
    )
    rows = (
        await session.execute(
            select(ClaimRow, func.coalesce(counts.c.evidence_count, 0))
            .outerjoin(counts, counts.c.claim_id == ClaimRow.id)
            .order_by(ClaimRow.created_at, ClaimRow.id)
        )
    ).all()
    return [
        ClaimSummary(
            id=claim.id,
            statement=claim.statement,
            review_status=claim.review_status,
            evidence_count=count,
            created_at=claim.created_at,
        )
        for claim, count in rows
    ]


async def get_claim(session: AsyncSession, claim_id: UUID) -> ClaimDetail | None:
    claim = await session.get(ClaimRow, claim_id)
    if claim is None:
        return None
    rows = (
        await session.execute(
            select(EvidenceRow, TextVersionRow, SourceRow)
            .join(TextVersionRow, TextVersionRow.id == EvidenceRow.version_id)
            .join(SourceRow, SourceRow.id == TextVersionRow.source_id)
            .where(EvidenceRow.claim_id == claim_id)
            .order_by(EvidenceRow.created_at, EvidenceRow.id)
        )
    ).all()
    evidence = [_entry_from(entry, version, source) for entry, version, source in rows]
    return ClaimDetail(claim=claim, evidence=evidence)


async def bind_evidence(
    session: AsyncSession, binding: EvidenceBinding
) -> tuple[EvidenceEntry, bool]:
    """Validate the citation against the stored version, then bind idempotently."""
    relation = normalize_relation(binding.relation)
    version = await session.get(TextVersionRow, binding.version_id)
    if version is None:
        raise NotFoundError("version", str(binding.version_id))
    if await session.get(ClaimRow, binding.claim_id) is None:
        raise NotFoundError("claim", str(binding.claim_id))
    locate_quote(
        TextVersion(version_id=str(version.id), text=version.content),
        Citation(
            version_id=str(version.id),
            start=binding.start,
            end=binding.end,
            exact_quote=binding.exact_quote,
        ),
    )
    existing = (
        await session.execute(
            select(EvidenceRow).where(
                EvidenceRow.claim_id == binding.claim_id,
                EvidenceRow.version_id == binding.version_id,
                EvidenceRow.start == binding.start,
                EvidenceRow.end == binding.end,
                EvidenceRow.relation == relation,
                EvidenceRow.note == binding.note,
            )
        )
    ).scalar_one_or_none()
    if existing is not None:
        return await _evidence_entry(session, existing.id), False
    evidence = EvidenceRow(
        id=uuid4(),
        claim_id=binding.claim_id,
        version_id=binding.version_id,
        start=binding.start,
        end=binding.end,
        relation=relation,
        note=binding.note,
    )
    session.add(evidence)
    await session.flush()
    return await _evidence_entry(session, evidence.id), True
