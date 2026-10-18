"""题录入库的验收（真实 PostgreSQL）。

对应[对话功能方案](../docs/chat-feature-plan-2026-10-18.md)第 6 节：题录只存书目字段，
出处写明来源库、链接与检索时间；重复导入命中既有来源，不重复建材料。
"""

from __future__ import annotations

from datetime import UTC, datetime

import pytest
import pytest_asyncio
from sqlalchemy import delete, func, select

from evidhist.db import create_engine, create_session_factory
from evidhist.db_migrations import apply_migrations
from evidhist.models import ClaimRow, EvidenceRow, SourceRow, TextVersionRow
from evidhist.research.chat_tools import import_paper_record
from evidhist.research.papers import PaperRecord

pytestmark = pytest.mark.integration

pytest_plugins = ["pytest_asyncio"]

RETRIEVED = datetime(2026, 10, 18, 12, 0, tzinfo=UTC)
RECORD = PaperRecord(
    sources=("openalex", "crossref"),
    title="The Defense of Beijing in 1449",
    authors=("Jiajin Li", "Ming Wang"),
    year=1998,
    venue="Ming Studies",
    doi="10.2307/1234",
    url="https://doi.org/10.2307/1234",
    retrieved_at=RETRIEVED,
)


@pytest_asyncio.fixture
async def migrated(database_url: str) -> str:
    engine = create_engine(database_url)
    await apply_migrations(engine)
    await engine.dispose()
    return database_url


@pytest_asyncio.fixture
async def store(migrated: str):
    engine = create_engine(migrated)
    factory = create_session_factory(engine)
    async with factory() as session:
        for table in (EvidenceRow, ClaimRow, TextVersionRow, SourceRow):
            await session.execute(delete(table))
        await session.commit()
    yield factory
    await engine.dispose()


async def test_a_paper_record_becomes_a_source_with_provenance(store) -> None:
    async with store() as session:
        result = await import_paper_record(session, RECORD)
        await session.commit()

        source = await session.get(SourceRow, __import__("uuid").UUID(str(result["source_id"])))
        version = await session.get(
            TextVersionRow, __import__("uuid").UUID(str(result["version_id"]))
        )

    assert result["created"] is True
    assert source is not None and version is not None
    assert source.title == "The Defense of Beijing in 1449"
    assert "openalex" in source.origin and "crossref" in source.origin
    assert "2026-10-18" in source.origin
    assert "CC0" in source.usage_terms
    assert "不得作为史料引文证据" in source.usage_terms
    assert "DOI：10.2307/1234" in version.content
    assert "检索时间：2026-10-18" in version.content
    assert version.label == "题录·1998"


async def test_reimporting_the_same_record_returns_the_existing_source(store) -> None:
    async with store() as session:
        first = await import_paper_record(session, RECORD)
        await session.commit()
        again = await import_paper_record(session, RECORD)
        await session.commit()

        sources = (await session.execute(select(func.count()).select_from(SourceRow))).scalar_one()
        versions = (
            await session.execute(select(func.count()).select_from(TextVersionRow))
        ).scalar_one()

    assert first["source_id"] == again["source_id"]
    assert first["version_id"] == again["version_id"]
    assert again["created"] is False
    assert (sources, versions) == (1, 1)


async def test_a_single_source_record_does_not_claim_crossref(store) -> None:
    single = PaperRecord(
        sources=("openalex",),
        title="Yu Qian and the Tumu Crisis",
        authors=(),
        year=2011,
        venue="Journal of Chinese History",
        doi="10.1017/S0001",
        url="https://doi.org/10.1017/S0001",
        retrieved_at=RETRIEVED,
    )
    async with store() as session:
        result = await import_paper_record(session, single)
        await session.commit()
        source = await session.get(SourceRow, __import__("uuid").UUID(str(result["source_id"])))

    assert source is not None
    assert "openalex" in source.origin
    assert "crossref" not in source.origin
    assert "Crossref" not in source.usage_terms
