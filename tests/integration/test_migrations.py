"""Migration runner acceptance: fresh databases apply every file in order exactly once.

The runner is also exercised against a brand-new empty database (not the shared
test database) so the "clean environment" path — the one documented for
installation — is actually executed, including the schema_migrations bookkeeping.
"""

from collections.abc import AsyncGenerator
from pathlib import Path

import pytest
import pytest_asyncio
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncConnection

from evidhist.db import create_engine
from evidhist.db_migrations import apply_migrations, available_migrations

pytestmark = pytest.mark.integration

TEMPORARY_DATABASE = "evidhist_migration_tmp"


async def _create_temporary_database(connection: AsyncConnection) -> None:
    await connection.execute(text(f'DROP DATABASE IF EXISTS "{TEMPORARY_DATABASE}"'))
    await connection.execute(text(f'CREATE DATABASE "{TEMPORARY_DATABASE}"'))


async def _drop_temporary_database(connection: AsyncConnection) -> None:
    await connection.execute(text(f'DROP DATABASE "{TEMPORARY_DATABASE}" WITH (FORCE)'))


def test_available_migrations_is_empty_for_a_missing_root(tmp_path: Path) -> None:
    assert available_migrations(tmp_path / "absent") == []


def test_available_migrations_sorts_files_by_name(tmp_path: Path) -> None:
    for name in ("0002_second.sql", "0001_first.sql", "0003_third.sql"):
        (tmp_path / name).write_text("-- empty\n", encoding="utf-8")

    assert [path.name for path in available_migrations(tmp_path)] == [
        "0001_first.sql",
        "0002_second.sql",
        "0003_third.sql",
    ]


@pytest_asyncio.fixture
async def fresh_database_url(database_url: str) -> AsyncGenerator[str]:
    """Create a brand-new empty database and yield its URL; drop it afterwards."""
    engine = create_engine(database_url)
    async with engine.connect() as connection:
        await connection.execution_options(isolation_level="AUTOCOMMIT")
        await _create_temporary_database(connection)
    await engine.dispose()
    yield database_url.rsplit("/", 1)[0] + "/" + TEMPORARY_DATABASE
    cleanup = create_engine(database_url)
    async with cleanup.connect() as connection:
        await connection.execution_options(isolation_level="AUTOCOMMIT")
        await _drop_temporary_database(connection)
    await cleanup.dispose()


async def test_fresh_database_applies_all_migrations_once(fresh_database_url: str) -> None:
    engine = create_engine(fresh_database_url)

    executed = await apply_migrations(engine)
    rerun = await apply_migrations(engine)

    async with engine.connect() as connection:
        tables = {
            row[0]
            for row in await connection.execute(
                text(
                    "SELECT table_name FROM information_schema.tables WHERE table_schema = 'public'"
                )
            )
        }
        recorded = {
            row[0] for row in await connection.execute(text("SELECT name FROM schema_migrations"))
        }
    await engine.dispose()

    assert executed == ["0001_init.sql"]
    assert rerun == []
    assert {"sources", "text_versions", "claims", "evidence", "schema_migrations"} <= tables
    assert recorded == {"0001_init.sql"}
