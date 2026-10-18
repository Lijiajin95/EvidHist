"""Versioned SQL migrations: each file applies once, in order, inside a transaction.

The migration directory lives at the repository root next to the source tree; the
runner records applied file names in the ``schema_migrations`` table and is safe
to re-run (pending-only). DDL runs inside a transaction so a failed migration
leaves no partial state.
"""

from pathlib import Path

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine

MIGRATIONS_ROOT = Path(__file__).resolve().parents[2] / "migrations"
MIGRATIONS_TABLE = "schema_migrations"

# 表名是模块常量，不是外部输入；SQL 值一律走绑定参数。bandit 的表名拼接告警在此豁免。
_CREATE_TABLE = (
    f"CREATE TABLE IF NOT EXISTS {MIGRATIONS_TABLE} ("
    "name text PRIMARY KEY, applied_at timestamptz NOT NULL DEFAULT now())"
)
_SELECT_APPLIED = f"SELECT name FROM {MIGRATIONS_TABLE}"  # nosec B608: 常量表名
_INSERT_APPLIED = f"INSERT INTO {MIGRATIONS_TABLE} (name) VALUES (:name)"  # nosec B608


async def applied_migrations(engine: AsyncEngine) -> set[str]:
    """Return already-applied migration file names, creating the bookkeeping table."""
    async with engine.begin() as connection:
        await connection.execute(text(_CREATE_TABLE))
        rows = await connection.execute(text(_SELECT_APPLIED))
        return {row[0] for row in rows}


def available_migrations(root: Path = MIGRATIONS_ROOT) -> list[Path]:
    """Sorted migration files; the runner applies pending files in name order."""
    return sorted(root.glob("*.sql")) if root.exists() else []


async def apply_migrations(engine: AsyncEngine, root: Path = MIGRATIONS_ROOT) -> list[str]:
    """Apply pending migrations in order and return the names that were applied."""
    files = available_migrations(root)
    applied = await applied_migrations(engine)
    executed: list[str] = []
    for path in files:
        if path.name in applied:
            continue
        statement = text(path.read_text(encoding="utf-8"))
        async with engine.begin() as connection:
            await connection.execute(statement)
            await connection.execute(
                text(_INSERT_APPLIED),
                {"name": path.name},
            )
        executed.append(path.name)
    return executed
