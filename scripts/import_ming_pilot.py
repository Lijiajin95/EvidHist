"""把试点所需卷次从 `crawler/data-ming/` 导入 EvidHist 材料库（M02）。

- **原文不改写**：直接保存 `raw/**` 的文本，内容 sha256 必须与 `manifest.jsonl` 登记一致，
  不一致即失败退出（不猜、不修补）。
- **幂等**：复用 `sources_service` 的自然键与内容散列，重复运行不新增来源或版本。
- **只复用既有能力**：一个作品一个来源，一卷一个不可变版本；不新增表、不新增接口。

用法：
    python scripts/import_ming_pilot.py --database-url postgresql+psycopg://…/evidhist_test
    python scripts/import_ming_pilot.py --dry-run      # 只核对文件与登记，不连数据库
    python scripts/import_ming_pilot.py --database-url … --json
退出码：0 成功；1 缺卷/散列不一致；2 未给数据库地址或数据库错误。
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
from dataclasses import dataclass
from pathlib import Path
from uuid import UUID

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from sqlalchemy.ext.asyncio import AsyncSession

from evidhist.db import create_engine, create_session_factory
from evidhist.domain.materials import content_sha256
from evidhist.sources_service import NewSource, add_version, create_source

REPO = Path(__file__).resolve().parents[1]
DATA_DIR = REPO / "crawler" / "data-ming"

# 试点卷次（见 docs/research/ming-pilot-materials-2026-10-18.md 与最小技术方案 §1）
PILOT_VOLUMES: dict[str, tuple[str, ...]] = {
    "明史": (
        "卷10",
        "卷11",
        "卷12",  # 本紀：英宗前紀、景帝、英宗後紀
        "卷167",
        "卷168",
        "卷169",
        "卷170",
        "卷171",
        "卷172",  # 列傳：土木死事、景泰内阁、于謙、奪門
        "卷89",
        "卷92",  # 兵志：京營/團營
    ),
    "明史紀事本末": ("卷32", "卷33"),  # 土木之變、景帝登極守禦
    "明通鑑": (
        "卷022",
        "卷023",
        "卷024",
        "卷025",
        "卷026",
        "卷027",  # 正統朝背景
        "卷028",
        "卷029",
        "卷030",
        "卷031",
        "卷032",
        "卷034",  # 土木至天順、成化雪獄
    ),
}


class MaterialGapError(RuntimeError):
    """缺少选定卷次或原文与登记不一致。"""


def _manifest_records() -> list[dict]:
    path = DATA_DIR / "manifest.jsonl"
    return [
        json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()
    ]


def latest_pages() -> dict[tuple[str, str], dict]:
    """按 (作品, 卷次) 取最新一条页面记录（台账只追加，后写覆盖先写）。"""
    latest: dict[tuple[str, str], dict] = {}
    for record in _manifest_records():
        if record.get("kind") in ("page", "alias"):
            latest[(record.get("work", ""), record.get("title", "").split("/")[-1])] = record
    return latest


def work_origins() -> dict[str, str]:
    origins: dict[str, str] = {}
    for record in _manifest_records():
        if record.get("kind") == "work":
            url = str(record.get("url", "")).split("?")[0]
            origins[record.get("work", "")] = f"中文维基文库 {url}"
    return origins


def load_volume(work: str, volume: str, pages: dict[tuple[str, str], dict]) -> tuple[str, dict]:
    """读一卷原文并核对登记；返回 (文本, 页面记录)。"""
    record = pages.get((work, volume))
    if record is None or record.get("status") != "stored":
        raise MaterialGapError(f"{work}/{volume}: manifest 中没有 stored 记录")
    text = (DATA_DIR / record["path"]).read_text(encoding="utf-8")
    digest = content_sha256(text)
    if digest != record.get("sha256"):
        raise MaterialGapError(
            f"{work}/{volume}: 内容散列 {digest[:12]} 与登记 {str(record.get('sha256'))[:12]} 不一致"
        )
    return text, record


def usage_terms(record: dict) -> str:
    license_info = record.get("license") or {}
    allowed = record.get("allowed_uses") or {}
    terms = f"{license_info.get('id', '许可未记录')}；{allowed.get('note', '')}".strip("；")
    if len(terms) > 500:  # 与 API 的 usage_terms 上限一致
        raise MaterialGapError("许可说明超过 500 字，需人工拆分")
    return terms


def version_label(volume: str, record: dict) -> str:
    modified = (record.get("version") or {}).get("modified", "未记录")
    label = f"{volume}|{modified}|sha256:{str(record.get('sha256'))[:12]}"
    if len(label) > 100:  # 与 API 的 label 上限一致
        raise MaterialGapError(f"版本标签超过 100 字：{label}")
    return label


def plan() -> list[tuple[str, str, str, dict]]:
    """返回 [(作品, 卷次, 原文, 页面记录)]，任何缺卷/散列不符都在这里失败。"""
    pages = latest_pages()
    items: list[tuple[str, str, str, dict]] = []
    for work, volumes in PILOT_VOLUMES.items():
        for volume in volumes:
            text, record = load_volume(work, volume, pages)
            items.append((work, volume, text, record))
    return items


@dataclass
class _ImportRun:
    """一次导入的会话与累计摘要。"""

    session: AsyncSession
    origins: dict[str, str]
    sources: dict[str, UUID]
    summary: dict


async def _import_volume(run: _ImportRun, item: tuple[str, str, str, dict]) -> None:
    """导入一卷：该作品首个卷次建立来源，其余卷次追加不可变版本。"""
    work, volume, text, record = item
    label = version_label(volume, record)
    if work not in run.sources:
        source, version, created = await create_source(
            run.session,
            NewSource(
                title=work,
                origin=run.origins[work],
                usage_terms=usage_terms(record),
                text=text,
                label=label,
            ),
        )
        run.sources[work] = source.id
        run.summary["sources_created"] += int(created)
    else:
        version, created = await add_version(
            run.session, source_id=run.sources[work], label=label, text=text
        )
    run.summary["versions_created" if created else "versions_existing"] += 1
    run.summary["volumes"].append(
        {
            "work": work,
            "volume": volume,
            "version_id": str(version.id),
            "sha256": version.content_sha256,
            "created": created,
            "label": version.label,
        }
    )


def _origins() -> dict[str, str]:
    origins = work_origins()
    fallback = "中文维基文库 https://zh.wikisource.org/"
    for work in PILOT_VOLUMES:
        origins[work] = origins.get(work) or origins.get("明史", fallback)
    return origins


async def import_materials(database_url: str, items: list[tuple[str, str, str, dict]]) -> dict:
    engine = create_engine(database_url)
    factory = create_session_factory(engine)
    summary: dict = {
        "sources_created": 0,
        "versions_created": 0,
        "versions_existing": 0,
        "volumes": [],
    }
    try:
        async with factory() as session:
            run = _ImportRun(session=session, origins=_origins(), sources={}, summary=summary)
            for item in items:
                await _import_volume(run, item)
            await session.commit()
    finally:
        await engine.dispose()
    return summary


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--database-url", default=None, help="PostgreSQL URL；默认取 EVIDHIST_DATABASE_URL"
    )
    parser.add_argument("--dry-run", action="store_true", help="只核对原文与登记，不连数据库")
    parser.add_argument("--json", action="store_true", help="以 JSON 输出摘要（最后一行）")
    args = parser.parse_args()

    try:
        items = plan()
    except MaterialGapError as error:
        print(f"材料核对失败：{error}", file=sys.stderr)
        return 1

    if args.dry_run:
        summary = {
            "dry_run": True,
            "works": len(PILOT_VOLUMES),
            "volumes": len(items),
            "verified": [f"{work}/{volume}" for work, volume, _, _ in items],
        }
    else:
        url = args.database_url or os.environ.get("EVIDHIST_DATABASE_URL")
        if url is None:
            print("需要 --database-url 或 EVIDHIST_DATABASE_URL，拒绝猜测目标库。", file=sys.stderr)
            return 2
        try:
            summary = asyncio.run(import_materials(url, items))
        except Exception as error:  # 数据库不可用或写入失败
            print(f"导入失败：{error}", file=sys.stderr)
            return 2

    if args.json:
        print(json.dumps(summary, ensure_ascii=False))
    else:
        print(f"作品 {len(PILOT_VOLUMES)} 部、卷次 {len(items)} 卷")
        print(
            f"新建版本 {summary.get('versions_created', 0)}，已存在 {summary.get('versions_existing', 0)}"
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
