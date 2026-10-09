"""Apply pending SQL migrations to a database; safe to re-run (pending only).

Usage: python scripts/migrate.py [--database-url URL] [--dry-run]
The URL defaults to EVIDHIST_DATABASE_URL; without it the script exits with an
error instead of guessing a target database. Each migration file runs inside
its own transaction and is recorded in schema_migrations.
"""

import argparse
import asyncio
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from evidhist.db import create_engine
from evidhist.db_migrations import apply_migrations, available_migrations


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--database-url",
        default=None,
        help="PostgreSQL URL; defaults to EVIDHIST_DATABASE_URL.",
    )
    parser.add_argument("--dry-run", action="store_true", help="List pending migrations only.")
    args = parser.parse_args()

    url = args.database_url or os.environ.get("EVIDHIST_DATABASE_URL")
    if url is None:
        print(
            "Refusing to guess a target database: pass --database-url or set "
            "EVIDHIST_DATABASE_URL.",
            file=sys.stderr,
        )
        return 2

    engine = create_engine(url)

    async def run() -> list[str]:
        if args.dry_run:
            return []
        applied = await apply_migrations(engine)
        await engine.dispose()
        return applied

    executed = asyncio.run(run())
    if args.dry_run:
        pending = [path.name for path in available_migrations()]
        print(f"Available migration files: {pending}")
    elif executed:
        print(f"Applied migrations: {executed}")
    else:
        print("No pending migrations.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
