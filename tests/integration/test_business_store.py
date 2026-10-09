"""Business store acceptance on the real PostgreSQL: migrations, idempotency,
immutable versions, persisted-version citation checks and restart survival.

The store is exercised through the service layer the API uses; HTTP behavior is
verified in component/system layers. Every case here states a user-visible
invariant from the night goal, not an implementation detail.
"""

import uuid

import pytest
import pytest_asyncio
from sqlalchemy import delete, func, select, text

from evidhist.claims_service import (
    EvidenceBinding,
    bind_evidence,
    create_claim,
    get_claim,
    list_claims,
)
from evidhist.db import create_engine, create_session_factory, session_scope
from evidhist.db_migrations import apply_migrations
from evidhist.domain.citations import CitationError
from evidhist.domain.materials import content_sha256
from evidhist.models import ClaimRow, EvidenceRow, SourceRow, TextVersionRow
from evidhist.sources_service import (
    NewSource,
    add_version,
    create_source,
    get_source,
    get_version,
    list_sources,
    locate_version,
)
from evidhist.store_errors import NotFoundError

pytestmark = pytest.mark.integration

pytest_plugins = ["pytest_asyncio"]


@pytest_asyncio.fixture
async def migrated(database_url: str) -> str:
    engine = create_engine(database_url)
    executed = await apply_migrations(engine)
    assert executed in (["0001_init.sql"], [])
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


async def read(factory, function, /, **kwargs):
    async with session_scope(factory) as session:
        return await function(session, **kwargs)


async def in_store(factory, query):
    async with factory() as session:
        return (await session.execute(query)).scalar()


async def count_rows(factory, table) -> int:
    return int(await in_store(factory, select(func.count()).select_from(table)))


SOURCE_INPUT = {
    "title": "史記·秦始皇本紀（合成整理本）",
    "origin": "合成材料，用於演示",
    "usage_terms": "合成材料，僅演示用途",
    "text": "帝曰：甲𠀀乙，命有司封禪。",
    "label": "整理初稿",
}


async def make_source(factory, **overrides):
    values = {**SOURCE_INPUT, **overrides}
    async with session_scope(factory) as session:
        source, version, created = await create_source(
            session,
            NewSource(
                title=values["title"],
                origin=values["origin"],
                usage_terms=values["usage_terms"],
                text=values["text"],
                label=values["label"],
            ),
        )
    return source, version, created


async def test_migrations_apply_once_and_rerun_is_a_noop(migrated: str) -> None:
    engine = create_engine(migrated)
    executed_again = await apply_migrations(engine)
    await engine.dispose()
    assert executed_again == []


async def test_source_creation_persists_the_initial_immutable_version(store) -> None:
    _source, version, created = await make_source(store)

    assert created is True
    assert version.content == SOURCE_INPUT["text"]
    assert version.content_sha256 == content_sha256(SOURCE_INPUT["text"])
    assert version.label == SOURCE_INPUT["label"]
    stored = await read(store, get_version, version_id=version.id)
    assert stored is not None and stored.content == SOURCE_INPUT["text"]
    assert await count_rows(store, SourceRow) == 1


async def test_duplicate_source_submission_returns_the_existing_rows(store) -> None:
    first_source, first_version, _first_created = await make_source(store)
    retry_source, retry_version, retry_created = await make_source(store)

    assert retry_created is False
    assert retry_source.id == first_source.id
    assert retry_version.id == first_version.id
    assert await count_rows(store, SourceRow) == 1
    assert await count_rows(store, TextVersionRow) == 1


async def test_same_text_with_different_origin_stays_separate_sources(store) -> None:
    source_a, version_a, created_a = await make_source(store)
    source_b, version_b, created_b = await make_source(store, origin="另一收藏，合成材料")

    assert created_a is True and created_b is True
    assert source_a.id != source_b.id
    assert version_a.id != version_b.id
    assert version_a.content == version_b.content
    assert await count_rows(store, SourceRow) == 2


async def test_adding_identical_content_returns_the_existing_version(store) -> None:
    _, first_version, _ = await make_source(store)
    async with session_scope(store) as session:
        again, created = await add_version(
            session, source_id=first_version.source_id, label="重试", text=SOURCE_INPUT["text"]
        )
    assert created is False
    assert again.id == first_version.id
    assert await count_rows(store, TextVersionRow) == 1


async def test_editing_text_creates_a_new_version_and_the_old_one_stays_readable(store) -> None:
    source, first_version, _ = await make_source(store)
    async with session_scope(store) as session:
        second_version, created = await add_version(
            session,
            source_id=source.id,
            label="校訂二稿",
            text="帝曰：甲𠀀乙，命有司封禪。補一句。",
        )

    assert created is True
    assert second_version.id != first_version.id
    old = await read(store, get_version, version_id=first_version.id)
    assert old is not None and old.content == SOURCE_INPUT["text"]
    detail = await read(store, get_source, source_id=source.id)
    assert detail is not None and len(detail.versions) == 2


async def test_locate_version_validates_offsets_and_quote_from_persisted_text(store) -> None:
    _, version, _ = await make_source(store)

    located = await read(
        store, locate_version, version_id=version.id, start=4, end=5, exact_quote="𠀀"
    )
    assert located.start == 4 and located.end == 5
    assert located.exact_quote == "𠀀"

    with pytest.raises(CitationError) as backwards:
        await read(store, locate_version, version_id=version.id, start=5, end=4, exact_quote="𠀀")
    assert backwards.value.code == "invalid_range"

    with pytest.raises(CitationError) as mismatch:
        await read(store, locate_version, version_id=version.id, start=4, end=5, exact_quote="甲")
    assert mismatch.value.code == "quote_mismatch"

    with pytest.raises(NotFoundError):
        await read(store, locate_version, version_id=uuid.uuid4(), start=0, end=1, exact_quote="甲")


async def test_source_list_supports_basic_filtering(store) -> None:
    await make_source(store)
    await make_source(
        store,
        title="漢書·高帝紀（合成整理本）",
        origin="合成材料，用於演示",
        text="高祖，沛豐邑中陽里人。",
    )

    all_sources = await read(store, list_sources, query=None)
    filtered = await read(store, list_sources, query="漢書")

    assert len(all_sources) == 2
    assert [s.title for s in filtered] == ["漢書·高帝紀（合成整理本）"]
    assert all(s.usage_terms for s in all_sources)


async def test_claim_creation_dedupes_on_the_exact_statement(store) -> None:
    async with session_scope(store) as session:
        claim, first_created = await create_claim(session, "秦始皇帝陵在驪山北麓。")
    async with session_scope(store) as session:
        retry, retry_created = await create_claim(session, "秦始皇帝陵在驪山北麓。")

    assert first_created is True and retry_created is False
    assert retry.id == claim.id
    assert claim.review_status == "unverified"
    assert await count_rows(store, ClaimRow) == 1


async def test_evidence_binding_validates_persists_and_dedupes(store) -> None:
    _, version, _ = await make_source(store)
    async with session_scope(store) as session:
        claim, _ = await create_claim(session, "始皇曾東巡封禪。")
    binding = EvidenceBinding(
        claim_id=claim.id,
        version_id=version.id,
        start=4,
        end=5,
        relation="supports",
        note="本紀明載",
        exact_quote="𠀀",
    )

    async with session_scope(store) as session:
        evidence, created = await bind_evidence(session, binding)
    assert created is True
    assert evidence.relation == "supports"

    async with session_scope(store) as session:
        retry, retry_created = await bind_evidence(session, binding)
    assert retry_created is False
    assert retry.id == evidence.id
    assert await count_rows(store, EvidenceRow) == 1


async def test_evidence_binding_rejects_invalid_citations_and_missing_rows(store) -> None:
    _, version, _ = await make_source(store)
    async with session_scope(store) as session:
        claim, _ = await create_claim(session, "另一句論斷。")

    with pytest.raises(CitationError) as bad_range:
        async with session_scope(store) as session:
            await bind_evidence(
                session,
                EvidenceBinding(
                    claim_id=claim.id,
                    version_id=version.id,
                    start=99,
                    end=100,
                    relation="supports",
                    note="",
                    exact_quote="甲",
                ),
            )
    assert bad_range.value.code == "invalid_range"

    with pytest.raises(NotFoundError):
        async with session_scope(store) as session:
            await bind_evidence(
                session,
                EvidenceBinding(
                    claim_id=uuid.uuid4(),
                    version_id=version.id,
                    start=4,
                    end=5,
                    relation="supports",
                    note="",
                    exact_quote="𠀀",
                ),
            )


async def test_claim_detail_joins_evidence_with_source_and_version(store) -> None:
    source, version, _ = await make_source(store)
    async with session_scope(store) as session:
        claim, _ = await create_claim(session, "始皇曾東巡封禪。")
    async with session_scope(store) as session:
        await bind_evidence(
            session,
            EvidenceBinding(
                claim_id=claim.id,
                version_id=version.id,
                start=4,
                end=5,
                relation="contradicts",
                note="另一派整理本無此句",
                exact_quote="𠀀",
            ),
        )

    detail = await read(store, get_claim, claim_id=claim.id)
    assert detail is not None
    assert detail.claim.statement == "始皇曾東巡封禪。"
    assert len(detail.evidence) == 1
    entry = detail.evidence[0]
    assert entry.source_title == source.title
    assert entry.version_id == version.id
    assert entry.quote == "𠀀"
    assert entry.relation == "contradicts"

    summaries = await read(store, list_claims)
    assert summaries[0].statement == "始皇曾東巡封禪。"
    assert summaries[0].evidence_count == 1


async def test_data_survives_engine_dispose_and_reconnect(store, migrated: str) -> None:
    _, version, _ = await make_source(store)
    async with session_scope(store) as session:
        claim, _ = await create_claim(session, "重啟後仍可回查。")
    async with session_scope(store) as session:
        await bind_evidence(
            session,
            EvidenceBinding(
                claim_id=claim.id,
                version_id=version.id,
                start=4,
                end=5,
                relation="mentions",
                note="",
                exact_quote="𠀀",
            ),
        )

    fresh_engine = create_engine(migrated)
    fresh_factory = create_session_factory(fresh_engine)
    reread = await read(fresh_factory, get_version, version_id=version.id)
    detail = await read(fresh_factory, get_claim, claim_id=claim.id)

    assert reread is not None and reread.content == SOURCE_INPUT["text"]
    assert detail is not None and len(detail.evidence) == 1
    row = await in_store(
        fresh_factory, text("SELECT count(*) FROM schema_migrations WHERE name = '0001_init.sql'")
    )
    assert row == 1
    await fresh_engine.dispose()


async def test_repeated_quote_at_two_positions_binds_both_without_merging(store) -> None:
    """同一字句在文本中出现两次时，两个显式区间各自成立且不合并。"""
    async with session_scope(store) as session:
        _source, version, _ = await create_source(
            session,
            NewSource(
                title="重複原句測試（合成）",
                origin="合成材料",
                usage_terms="合成材料",
                text="甲乙甲丙",
                label="初稿",
            ),
        )
        claim, _ = await create_claim(session, "重複原句各自定位。")

    for position in (0, 2):
        async with session_scope(store) as session:
            _entry, created = await bind_evidence(
                session,
                EvidenceBinding(
                    claim_id=claim.id,
                    version_id=version.id,
                    start=position,
                    end=position + 1,
                    relation="supports",
                    note=f"第 {position + 1} 處出現",
                    exact_quote="甲",
                ),
            )
        assert created is True

    detail = await read(store, get_claim, claim_id=claim.id)
    assert detail is not None
    assert len(detail.evidence) == 2
    positions = sorted((entry.start, entry.end) for entry in detail.evidence)
    assert positions == [(0, 1), (2, 3)]
    assert all(entry.quote == "甲" for entry in detail.evidence)
    assert len({entry.id for entry in detail.evidence}) == 2


async def test_evidence_still_resolves_against_its_old_version_after_new_versions(store) -> None:
    """材料新增版本后，既有证据仍按其绑定的旧版本回查字句。"""
    async with session_scope(store) as session:
        _, version, _ = await create_source(
            session,
            NewSource(
                title="舊引用回查（合成）",
                origin="合成材料",
                usage_terms="合成材料",
                text="舊版本原句。",
                label="初稿",
            ),
        )
        claim, _ = await create_claim(session, "舊引用在版本更換後仍可回查。")
    async with session_scope(store) as session:
        await bind_evidence(
            session,
            EvidenceBinding(
                claim_id=claim.id,
                version_id=version.id,
                start=0,
                end=2,
                relation="mentions",
                note="",
                exact_quote="舊版",
            ),
        )
    async with session_scope(store) as session:
        await add_version(
            session, source_id=version.source_id, label="二稿", text="新版本原句，改寫。"
        )

    detail = await read(store, get_claim, claim_id=claim.id)
    assert detail is not None
    assert len(detail.evidence) == 1
    assert detail.evidence[0].quote == "舊版"
    assert detail.evidence[0].version_id == version.id


async def test_source_search_treats_wildcards_as_literal_text(store) -> None:
    await make_source(store)
    await make_source(
        store,
        title="漢書·高帝紀（合成整理本）",
        origin="合成材料，用於演示",
        text="高祖，沛豐邑中陽里人。",
    )

    percent = await read(store, list_sources, query="%")
    underscore = await read(store, list_sources, query="_")
    literal = await read(store, list_sources, query="史記")

    assert percent == [] and underscore == []
    assert [s.title for s in literal] == [SOURCE_INPUT["title"]]
