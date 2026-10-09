"""Seed the demo database with two clearly-marked synthetic Chinese materials.

The materials are synthetic demonstration data (合成材料), not historical
transcriptions; the demo shows the source/version/claim/evidence loop with
multi-source disagreement while stating clearly that nothing is verified.
"""

import argparse
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from evidhist.claims_service import EvidenceBinding, bind_evidence, create_claim
from evidhist.db import create_engine, create_session_factory, session_scope
from evidhist.db_migrations import apply_migrations
from evidhist.sources_service import NewSource, create_source

DEMO_DATABASE_URL = "postgresql+psycopg://evidhist:evidhist@127.0.0.1:55433/evidhist_demo"

MATERIAL_A = NewSource(
    title="史記·秦始皇本紀（合成演示本 A）",
    origin="合成材料，用於演示，非史籍轉錄",
    usage_terms="合成材料，僅演示用途",
    text="帝曰：甲𠀀乙，命有司封禪。東巡郡縣，祠鄒嶧山。",
    label="演示整理初稿",
)
MATERIAL_B = NewSource(
    title="史記·秦始皇本紀（合成演示本 B，異文）",
    origin="合成材料，用於演示，非史籍轉錄",
    usage_terms="合成材料，僅演示用途",
    text="帝曰：甲乙，命有司封禪。東巡郡縣，祠鄒嶧山，刻石頌功。",
    label="演示異文本",
)


async def seed(url: str) -> None:
    engine = create_engine(url)
    await apply_migrations(engine)
    factory = create_session_factory(engine)
    async with session_scope(factory) as session:
        _, version_a, _ = await create_source(session, MATERIAL_A)
        _, version_b, _ = await create_source(session, MATERIAL_B)
        claim, _ = await create_claim(session, "秦始皇曾東巡並封禪。")
        # 帝(0)曰(1)：(2)甲(3)𠀀(4)乙(5)，(6) → [4,5) 為 𠀀；B 本 [4,5) 為 乙（無 𠀀 字）。
        await bind_evidence(
            session,
            EvidenceBinding(
                claim_id=claim.id,
                version_id=version_a.id,
                start=4,
                end=5,
                relation="supports",
                note="演示本 A 載有此字",
                exact_quote="𠀀",
            ),
        )
        await bind_evidence(
            session,
            EvidenceBinding(
                claim_id=claim.id,
                version_id=version_b.id,
                start=4,
                end=5,
                relation="insufficient",
                note="演示本 B 無 𠀀 字，此處字句不同",
                exact_quote="乙",
            ),
        )
    await engine.dispose()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--database-url", default=DEMO_DATABASE_URL)
    args = parser.parse_args()
    asyncio.run(seed(args.database_url))
    print("Demo data seeded: two synthetic materials, one claim, two evidence bindings.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
