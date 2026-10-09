"""Sources and immutable text versions: creation with natural-key idempotency.

A source holds descriptive metadata; its text lives in immutable versions keyed
by the SHA-256 of the exact content. Retrying a creation with the same natural
key returns the existing rows instead of duplicating them; identical text under
a different origin remains a separate source (same content never merges
collections). Citation checks against a persisted version reuse the pure
domain rule from :mod:`evidhist.domain.citations`.
"""

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from evidhist.domain.citations import Citation, TextVersion, locate_quote
from evidhist.domain.materials import content_sha256
from evidhist.models import SourceRow, TextVersionRow
from evidhist.store_errors import NotFoundError


@dataclass(frozen=True)
class NewSource:
    title: str
    origin: str
    usage_terms: str
    text: str
    label: str


@dataclass(frozen=True)
class SourceSummary:
    id: UUID
    title: str
    origin: str
    usage_terms: str
    version_count: int
    created_at: datetime


@dataclass(frozen=True)
class SourceDetail:
    source: SourceRow
    versions: list[TextVersionRow]


async def create_source(
    session: AsyncSession, new_source: NewSource
) -> tuple[SourceRow, TextVersionRow, bool]:
    """Create a source with its first version; an exact retry returns the existing rows."""
    digest = content_sha256(new_source.text)
    existing = (
        await session.execute(
            select(SourceRow, TextVersionRow)
            .join(TextVersionRow, TextVersionRow.source_id == SourceRow.id)
            .where(
                SourceRow.title == new_source.title,
                SourceRow.origin == new_source.origin,
                SourceRow.usage_terms == new_source.usage_terms,
                TextVersionRow.content_sha256 == digest,
            )
            .limit(1)
        )
    ).first()
    if existing is not None:
        return existing[0], existing[1], False
    source = SourceRow(
        id=uuid4(),
        title=new_source.title,
        origin=new_source.origin,
        usage_terms=new_source.usage_terms,
    )
    version = TextVersionRow(
        id=uuid4(),
        source_id=source.id,
        label=new_source.label,
        content=new_source.text,
        content_sha256=digest,
    )
    session.add_all([source, version])
    await session.flush()
    return source, version, True


async def add_version(
    session: AsyncSession, *, source_id: UUID, label: str, text: str
) -> tuple[TextVersionRow, bool]:
    """Add an immutable version; identical content for the source returns the stored one."""
    if await session.get(SourceRow, source_id) is None:
        raise NotFoundError("source", str(source_id))
    digest = content_sha256(text)
    existing = (
        await session.execute(
            select(TextVersionRow).where(
                TextVersionRow.source_id == source_id,
                TextVersionRow.content_sha256 == digest,
            )
        )
    ).scalar_one_or_none()
    if existing is not None:
        return existing, False
    version = TextVersionRow(
        id=uuid4(),
        source_id=source_id,
        label=label,
        content=text,
        content_sha256=digest,
    )
    session.add(version)
    await session.flush()
    return version, True


async def get_source(session: AsyncSession, source_id: UUID) -> SourceDetail | None:
    source = await session.get(SourceRow, source_id)
    if source is None:
        return None
    versions = (
        (
            await session.execute(
                select(TextVersionRow)
                .where(TextVersionRow.source_id == source_id)
                .order_by(TextVersionRow.created_at, TextVersionRow.id)
            )
        )
        .scalars()
        .all()
    )
    return SourceDetail(source=source, versions=list(versions))


async def get_version(session: AsyncSession, version_id: UUID) -> TextVersionRow | None:
    return await session.get(TextVersionRow, version_id)


async def list_sources(session: AsyncSession, *, query: str | None) -> list[SourceSummary]:
    """List sources with version counts; a query filters title and origin."""
    counts = (
        select(TextVersionRow.source_id, func.count().label("version_count"))
        .group_by(TextVersionRow.source_id)
        .subquery()
    )
    statement = (
        select(
            SourceRow,
            func.coalesce(counts.c.version_count, 0).label("version_count"),
        )
        .outerjoin(counts, counts.c.source_id == SourceRow.id)
        .order_by(SourceRow.created_at, SourceRow.id)
    )
    if query:
        escaped = query.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
        pattern = f"%{escaped}%"
        statement = statement.where(
            SourceRow.title.ilike(pattern, escape="\\")
            | SourceRow.origin.ilike(pattern, escape="\\")
        )
    rows = (await session.execute(statement)).all()
    return [
        SourceSummary(
            id=source.id,
            title=source.title,
            origin=source.origin,
            usage_terms=source.usage_terms,
            version_count=count,
            created_at=source.created_at,
        )
        for source, count in rows
    ]


async def locate_version(
    session: AsyncSession, *, version_id: UUID, start: int, end: int, exact_quote: str
):
    """Validate a citation against the persisted, immutable version text."""
    version = await session.get(TextVersionRow, version_id)
    if version is None:
        raise NotFoundError("version", str(version_id))
    return locate_quote(
        TextVersion(version_id=str(version.id), text=version.content),
        Citation(version_id=str(version.id), start=start, end=end, exact_quote=exact_quote),
    )
