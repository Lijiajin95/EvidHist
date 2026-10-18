"""试点材料导入的验收（真实 PostgreSQL）。

对应[首版最小技术方案](../docs/minimal-technical-plan-2026-10-18.md)步骤 1 与 §9：

- 25 卷 raw 原文以 sha256 为身份入库，内容逐字不改写；
- 重复导入幂等（不新增版本、不新增来源）；
- 入库版本可直接用于引文硬校验（M04）。

测试独立核对语料目录的原始文件与 `manifest.jsonl`，不复用导入脚本内部的选材或散列计算。
本地提供 `crawler/data-ming/` 时直接核对真实 25 卷；该目录不随代码发布（CI 无此目录）时，
按同样的目录与登记结构生成合成语料，断言不变，从而在两种环境都真实执行导入路径。
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest
import pytest_asyncio
from sqlalchemy import delete, func, select

from evidhist.db import create_engine, create_session_factory
from evidhist.db_migrations import apply_migrations
from evidhist.domain.citations import CitationError
from evidhist.domain.materials import content_sha256
from evidhist.models import ClaimRow, EvidenceRow, SourceRow, TextVersionRow
from evidhist.sources_service import locate_version

pytestmark = pytest.mark.integration

pytest_plugins = ["pytest_asyncio"]

REPO = Path(__file__).resolve().parents[2]
SCRIPT = REPO / "scripts" / "import_ming_pilot.py"
DATA = REPO / "crawler" / "data-ming"

# 试点卷次（独立于实现写出预期，共 25 卷）
PILOT_VOLUMES: dict[str, tuple[str, ...]] = {
    "明史": (
        "卷10",
        "卷11",
        "卷12",
        "卷167",
        "卷168",
        "卷169",
        "卷170",
        "卷171",
        "卷172",
        "卷89",
        "卷92",
    ),
    "明史紀事本末": ("卷32", "卷33"),
    "明通鑑": (
        "卷022",
        "卷023",
        "卷024",
        "卷025",
        "卷026",
        "卷027",
        "卷028",
        "卷029",
        "卷030",
        "卷031",
        "卷032",
        "卷034",
    ),
}
EXPECTED_TOTAL = sum(len(volumes) for volumes in PILOT_VOLUMES.values())


SYNTHETIC_SENTENCE = "于謙守京師，戒嚴九門。"


def build_synthetic_corpus(root: Path) -> Path:
    """生成与真实语料同构的 25 卷语料：raw 文本 + 追加式 manifest.jsonl。"""
    raw = root / "raw"
    raw.mkdir(parents=True, exist_ok=True)
    records: list[dict] = []
    for work, volumes in PILOT_VOLUMES.items():
        records.append(
            {"kind": "work", "work": work, "url": f"https://zh.wikisource.org/wiki/{work}"}
        )
        for volume in volumes:
            name = f"{work}-{volume}.txt"
            lead = "于謙傳。" if (work, volume) == ("明史", "卷170") else ""
            text = f"{lead}{volume}記事。{SYNTHETIC_SENTENCE}"
            (raw / name).write_text(text, encoding="utf-8")
            records.append(
                {
                    "kind": "page",
                    "work": work,
                    "title": f"{work}/{volume}",
                    "status": "stored",
                    "path": f"raw/{name}",
                    "sha256": content_sha256(text),
                    "version": {"modified": "2026-10-18"},
                    "license": {"id": "CC BY-SA 4.0"},
                    "allowed_uses": {"note": "合成语料，仅用于集成测试。"},
                }
            )
    lines = [json.dumps(record, ensure_ascii=False) for record in records]
    (root / "manifest.jsonl").write_text("\n".join(lines) + "\n", encoding="utf-8")
    return root


@pytest.fixture(scope="session")
def corpus(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """真实语料优先；CI 等无本地语料的环境使用同构合成语料。

    设 EVIDHIST_MING_CORPUS=synthetic 可强制走合成语料，便于在本地核对 CI 分支。
    """
    if os.environ.get("EVIDHIST_MING_CORPUS") == "synthetic":
        return build_synthetic_corpus(tmp_path_factory.mktemp("ming-corpus"))
    if (DATA / "manifest.jsonl").exists():
        return DATA
    return build_synthetic_corpus(tmp_path_factory.mktemp("ming-corpus"))


def manifest_pages(root: Path) -> dict[tuple[str, str], dict]:
    """最新状态为 stored 的页面记录，按 (作品, 卷次) 索引。"""
    latest: dict[tuple[str, str], dict] = {}
    for line in (root / "manifest.jsonl").read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        record = json.loads(line)
        if record.get("kind") in ("page", "alias"):
            latest[(record.get("work", ""), record.get("title", ""))] = record
    return {
        (work, title.split("/")[-1]): record
        for (work, title), record in latest.items()
        if record.get("status") == "stored"
    }


def run_import(database_url: str, root: Path) -> dict:
    result = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--database-url",
            database_url,
            "--data-dir",
            str(root),
            "--json",
        ],
        capture_output=True,
        text=True,
        cwd=REPO,
        check=False,
    )
    assert result.returncode == 0, f"导入脚本失败：{result.stderr[-2000:]}"
    return json.loads(result.stdout.strip().splitlines()[-1])


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


async def version_count(factory) -> int:
    async with factory() as session:
        return int(
            (await session.execute(select(func.count()).select_from(TextVersionRow))).scalar_one()
        )


async def test_import_stores_every_pilot_volume_byte_for_byte(
    store, migrated: str, corpus: Path
) -> None:
    summary = run_import(migrated, corpus)
    assert summary["versions_created"] == EXPECTED_TOTAL
    assert summary["versions_existing"] == 0
    assert {volume["work"] for volume in summary["volumes"]} == set(PILOT_VOLUMES)

    pages = manifest_pages(corpus)
    async with store() as session:
        rows = (
            await session.execute(
                select(SourceRow.title, TextVersionRow).join(
                    TextVersionRow, TextVersionRow.source_id == SourceRow.id
                )
            )
        ).all()
        usage_terms = {
            source.title: source.usage_terms
            for source in (await session.execute(select(SourceRow))).scalars()
        }
    assert len(rows) == EXPECTED_TOTAL
    seen: set[tuple[str, str]] = set()
    for title, version in rows:
        volume = version.label.split("|")[0]
        seen.add((title, volume))
        record = pages[(title, volume)]
        assert version.content_sha256 == record["sha256"], (
            f"{title}/{volume} 散列与 manifest 不一致"
        )
        assert content_sha256(version.content) == record["sha256"]
        assert version.content == (corpus / record["path"]).read_text(encoding="utf-8")
        assert "CC BY-SA" in usage_terms[title]
    assert seen == {(work, volume) for work, volumes in PILOT_VOLUMES.items() for volume in volumes}


async def test_import_is_idempotent(store, migrated: str, corpus: Path) -> None:
    first = run_import(migrated, corpus)
    second = run_import(migrated, corpus)
    assert first["versions_created"] == EXPECTED_TOTAL
    assert second["versions_created"] == 0
    assert second["versions_existing"] == EXPECTED_TOTAL
    assert await version_count(store) == EXPECTED_TOTAL


async def test_imported_version_serves_citation_check(store, migrated: str, corpus: Path) -> None:
    run_import(migrated, corpus)
    async with store() as session:
        row = (
            await session.execute(
                select(TextVersionRow)
                .join(SourceRow, SourceRow.id == TextVersionRow.source_id)
                .where(SourceRow.title == "明史", TextVersionRow.label.like("卷170|%"))
            )
        ).scalar_one()

        start = row.content.index("于謙")
        located = await locate_version(
            session, version_id=row.id, start=start, end=start + 2, exact_quote="于謙"
        )
        assert located.exact_quote == "于謙"
        assert located.start == start

        with pytest.raises(CitationError) as error:
            await locate_version(
                session, version_id=row.id, start=start, end=start + 2, exact_quote="于謙傳"
            )
        assert error.value.code == "quote_mismatch"


RUN_SCRIPT = REPO / "scripts" / "run_research.py"


def run_cli(database_url: str, runs_dir: Path, run_id: str) -> dict:
    result = subprocess.run(
        [
            sys.executable,
            str(RUN_SCRIPT),
            "--database-url",
            database_url,
            "--question",
            "于謙在京城守禦中的主張是什麼?",
            "--executor",
            "fake",
            "--reviewer",
            "fake",
            "--run-id",
            run_id,
            "--runs-dir",
            str(runs_dir),
            "--json",
        ],
        capture_output=True,
        text=True,
        cwd=REPO,
        check=False,
    )
    assert result.returncode == 0, f"运行入口失败：{result.stderr[-2000:]}"
    return json.loads(result.stdout.strip().splitlines()[-1])


async def test_cli_run_persists_claims_evidence_and_artifacts(
    store, migrated: str, corpus: Path, tmp_path: Path
) -> None:
    run_import(migrated, corpus)
    runs_dir = tmp_path / "runs"
    summary = run_cli(migrated, runs_dir, "it-run")

    assert summary["verified"] >= 1
    assert summary["stopped_reason"] is None
    assert summary["persisted"]["claims"] >= 1
    assert summary["persisted"]["evidence"] >= 1
    for name in ("report.md", "citations.json", "run.json", "review.json"):
        assert (runs_dir / "it-run" / name).exists(), name

    async with store() as session:
        claims = (await session.execute(select(func.count()).select_from(ClaimRow))).scalar_one()
        rows = (
            await session.execute(
                select(EvidenceRow, TextVersionRow).join(
                    TextVersionRow, TextVersionRow.id == EvidenceRow.version_id
                )
            )
        ).all()
    assert claims >= 1
    assert rows
    for evidence, version in rows:
        assert 0 <= evidence.start < evidence.end <= len(version.content)
        assert version.content[evidence.start : evidence.end]
        assert evidence.relation == "supports"
