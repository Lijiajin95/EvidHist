import pytest
from fastapi.testclient import TestClient
from pydantic import SecretStr
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import create_async_engine

from evidhist.api import create_app
from evidhist.settings import Settings

pytestmark = pytest.mark.integration


def test_api_readiness_uses_a_real_postgres_connection(database_url: str) -> None:
    with TestClient(create_app(settings=Settings(database_url=SecretStr(database_url)))) as client:
        response = client.get("/health/ready")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


async def test_parameter_binding_preserves_quote_text_and_transactions_recover(
    database_url: str,
) -> None:
    engine = create_async_engine(database_url)
    try:
        async with engine.begin() as connection:
            await connection.execute(
                text(
                    "CREATE TEMP TABLE quote_probe (version_id TEXT PRIMARY KEY, quote TEXT) ON COMMIT DROP"
                )
            )
            await connection.execute(
                text("INSERT INTO quote_probe VALUES (:id, :quote)"),
                {"id": "v1", "quote": "甲'; DROP TABLE quote_probe; --"},
            )
            with pytest.raises(IntegrityError):
                async with connection.begin_nested():
                    await connection.execute(
                        text("INSERT INTO quote_probe VALUES (:id, :quote)"),
                        {"id": "v1", "quote": "another quote"},
                    )
            result = await connection.execute(
                text("SELECT quote FROM quote_probe WHERE version_id = :id"), {"id": "v1"}
            )
            assert result.scalar_one() == "甲'; DROP TABLE quote_probe; --"
    finally:
        await engine.dispose()


async def test_pgvector_exact_search_respects_version_filter(database_url: str) -> None:
    engine = create_async_engine(database_url)
    try:
        async with engine.begin() as connection:
            await connection.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
            await connection.execute(
                text(
                    "CREATE TEMP TABLE embedding_probe (version_id TEXT, embedding vector(3)) ON COMMIT DROP"
                )
            )
            await connection.execute(
                text("INSERT INTO embedding_probe VALUES (:id, CAST(:embedding AS vector))"),
                [{"id": "a", "embedding": "[1,0,0]"}, {"id": "b", "embedding": "[0,1,0]"}],
            )
            result = await connection.execute(
                text(
                    "SELECT version_id FROM embedding_probe WHERE version_id = :id ORDER BY embedding <-> CAST(:query AS vector) LIMIT 1"
                ),
                {"id": "b", "query": "[1,0,0]"},
            )
            assert result.scalar_one() == "b"
    finally:
        await engine.dispose()
