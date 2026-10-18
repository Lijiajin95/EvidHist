"""跑一次最小研究闭环，并把运行产物与论断/证据落库（M01/M06）。

用法：
    python scripts/run_research.py --database-url postgresql+psycopg://…/evidhist_demo \
        --question "于謙在北京保衛戰中的作用是什麼?" [--executor fake|pi] [--reviewer none|fake|pi]
    python scripts/run_research.py --database-url … --question … --dry-run   # 只列材料，不运行
退出码：0 完成（含如实记录的中止）；1 无材料；2 参数或数据库错误。
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
from datetime import UTC, datetime
from pathlib import Path
from uuid import UUID

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from evidhist.claims_service import EvidenceBinding, bind_evidence, create_claim
from evidhist.db import create_engine, create_session_factory, session_scope
from evidhist.models import SourceRow, TextVersionRow
from evidhist.research.executor import FakeExecutor, ResearchExecutor, RunLimits
from evidhist.research.graph import ResearchJob, ResearchResult, run_research
from evidhist.research.pi_executor import PiExecutor
from evidhist.research.pi_rpc import PiConfig
from evidhist.research.report import save_run
from evidhist.research.review import FakeReviewer, PiReviewer, Reviewer
from evidhist.research.tools import Material

REPO = Path(__file__).resolve().parents[1]


async def load_materials(session: AsyncSession, works: tuple[str, ...]) -> list[Material]:
    """从材料库读出已导入的卷次，按作品/卷次排序。"""
    statement = (
        select(SourceRow.title, TextVersionRow)
        .join(TextVersionRow, TextVersionRow.source_id == SourceRow.id)
        .order_by(SourceRow.title, TextVersionRow.label)
    )
    if works:
        statement = statement.where(SourceRow.title.in_(works))
    rows = (await session.execute(statement)).all()
    return [
        Material(
            version_id=str(version.id),
            work=title,
            volume=version.label.split("|")[0],
            text=version.content,
        )
        for title, version in rows
    ]


def build_executor(args: argparse.Namespace, run_id: str) -> ResearchExecutor:
    if args.executor == "fake":
        return FakeExecutor(mode="ok")
    home = Path(args.pi_home).resolve()
    return PiExecutor(
        PiConfig(
            provider=args.provider,
            model=args.model,
            home=home,
            session_dir=home / "sessions" / run_id,
            workdir=home,
            command=args.pi_command,
            bin_dir=Path(args.pi_bin_dir).resolve(),
            thinking=args.thinking,
        )
    )


def build_reviewer(args: argparse.Namespace, run_id: str) -> Reviewer | None:
    if args.reviewer == "none":
        return None
    if args.reviewer == "fake":
        return FakeReviewer()
    home = Path(args.pi_home).resolve()
    return PiReviewer(
        PiConfig(
            provider=args.provider,
            model=args.model,
            home=home,
            session_dir=home / "sessions" / f"{run_id}-review",
            workdir=home,
            command=args.pi_command,
            bin_dir=Path(args.pi_bin_dir).resolve(),
            thinking=args.thinking,
        )
    )


async def persist_claims(session: AsyncSession, result: ResearchResult) -> dict[str, int]:
    """把通过程序校验的论断与其引文写入材料库（供工作台复核）。"""
    claims_written = evidence_written = skipped = 0
    for verdict in result.claims:
        if not verdict.ok:
            skipped += 1
            continue
        claim, _created = await create_claim(session, verdict.statement)
        claims_written += 1
        for item in verdict.citations:
            _evidence, created = await bind_evidence(
                session,
                EvidenceBinding(
                    claim_id=claim.id,
                    version_id=UUID(item.citation.version_id),
                    start=item.citation.start,
                    end=item.citation.end,
                    relation="supports",
                    note=f"run {result.run_id} 程序校验通过",
                    exact_quote=item.citation.exact_quote,
                ),
            )
            evidence_written += int(created)
    return {"claims": claims_written, "evidence": evidence_written, "skipped": skipped}


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--database-url", default=None, help="PostgreSQL URL；默认 EVIDHIST_DATABASE_URL"
    )
    parser.add_argument("--question", required=True, help="研究问题（M01）")
    parser.add_argument("--executor", choices=("fake", "pi"), default="fake")
    parser.add_argument("--reviewer", choices=("none", "fake", "pi"), default="none")
    parser.add_argument("--works", default="", help="只使用这些作品（逗号分隔，默认全部）")
    parser.add_argument("--runs-dir", default=str(REPO / "runs"))
    parser.add_argument("--run-id", default=None)
    parser.add_argument("--wall-seconds", type=int, default=1200)
    parser.add_argument("--tool-calls", type=int, default=60)
    parser.add_argument("--provider", default="cc-switch-open-code-go")
    parser.add_argument("--model", default="deepseek-v4.1-flash")
    parser.add_argument("--pi-command", default="pi")
    parser.add_argument("--thinking", default="minimal", help="PI 思考级别（off/minimal/low/…）")
    parser.add_argument("--pi-home", default=str(REPO / ".cache" / "pi-home"))
    parser.add_argument("--pi-bin-dir", default=str(Path.home() / ".pi" / "agent" / "bin"))
    parser.add_argument("--dry-run", action="store_true", help="只列材料与配置，不运行")
    parser.add_argument("--json", action="store_true", help="以 JSON 输出摘要")
    return parser.parse_args(argv)


async def execute(
    args: argparse.Namespace,
    factory: async_sessionmaker[AsyncSession],
    materials: list[Material],
    run_id: str,
) -> tuple[ResearchResult, dict[str, int], str]:
    """跑一次闭环并落盘、落库；返回结果、写入统计与产物目录。"""
    executor = build_executor(args, run_id)
    result = await run_research(
        executor=executor,
        materials=materials,
        job=ResearchJob(
            question=args.question,
            run_id=run_id,
            limits=RunLimits(wall_seconds=args.wall_seconds, tool_calls=args.tool_calls),
            reviewer=build_reviewer(args, run_id),
        ),
    )
    artifacts = save_run(
        Path(args.runs_dir) / run_id,
        result,
        executor_name=executor.executor_name,
        saved_at=datetime.now(UTC).isoformat(),
    )
    async with session_scope(factory) as session:
        persisted = await persist_claims(session, result)
    return result, persisted, str(artifacts.directory)


def summarize(
    run_id: str,
    material_count: int,
    result: ResearchResult,
    persisted: dict[str, int],
    artifacts: str,
) -> dict[str, object]:
    return {
        "run_id": run_id,
        "executor": "pi" if result.usage.get("provider") else "fake",
        "materials": material_count,
        "claims": len(result.claims),
        "verified": sum(1 for claim in result.claims if claim.ok),
        "insufficient": len(result.insufficient),
        "stopped_reason": result.stopped_reason,
        "tool_calls": result.tool_calls,
        "usage": result.usage,
        "review": None if result.review is None else result.review.verdict,
        "persisted": persisted,
        "artifacts": artifacts,
    }


async def run(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    url = args.database_url or os.environ.get("EVIDHIST_DATABASE_URL")
    if url is None:
        print("需要 --database-url 或 EVIDHIST_DATABASE_URL，拒绝猜测目标库。", file=sys.stderr)
        return 2
    run_id = args.run_id or datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    works = tuple(part for part in args.works.split(",") if part)
    engine = create_engine(url)
    factory = create_session_factory(engine)
    try:
        async with session_scope(factory) as session:
            materials = await load_materials(session, works)
        if not materials:
            print("材料库为空：先运行 scripts/import_ming_pilot.py。", file=sys.stderr)
            return 1
        if args.dry_run:
            print(json.dumps({"run_id": run_id, "materials": len(materials)}, ensure_ascii=False))
            return 0
        result, persisted, artifacts = await execute(args, factory, materials, run_id)
    except Exception as error:  # 数据库不可用或运行时异常
        print(f"运行失败：{error}", file=sys.stderr)
        return 2
    finally:
        await engine.dispose()

    summary = summarize(run_id, len(materials), result, persisted, artifacts)
    print(
        json.dumps(summary, ensure_ascii=False)
        if args.json
        else json.dumps(summary, ensure_ascii=False, indent=2)
    )
    return 0


def main() -> int:
    return asyncio.run(run())


if __name__ == "__main__":
    sys.exit(main())
