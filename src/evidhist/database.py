from typing import Protocol

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine


class DatabaseProbe(Protocol):
    async def check(self) -> None: ...

    async def close(self) -> None: ...


class PostgresDatabase:
    """A readiness probe and lifecycle boundary; business persistence will use migrations."""

    def __init__(self, url: str) -> None:
        self._engine = create_async_engine(
            url,
            pool_pre_ping=True,
            pool_timeout=5,
            connect_args={"connect_timeout": 5},
        )

    async def check(self) -> None:
        async with self._engine.connect() as connection:
            await connection.execute(text("SELECT 1"))

    async def close(self) -> None:
        await self._engine.dispose()
