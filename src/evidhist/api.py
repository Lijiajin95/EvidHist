"""FastAPI application: health, the explicit-text locate tool and the v0.1 business API.

The explicit-text ``POST /v1/quotes/locate`` keeps its tool semantics: it checks
a citation against text supplied in the request itself. The product flow uses
the persisted-version endpoints under ``/v1/sources``, ``/v1/versions`` and
``/v1/claims``.
"""

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from json import dumps as json_dumps

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse, Response
from pydantic import BaseModel, ConfigDict
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

from evidhist.api_claims import router as claims_router
from evidhist.api_sources import router as sources_router
from evidhist.database import DatabaseProbe, PostgresDatabase
from evidhist.db import create_engine, create_session_factory
from evidhist.domain.citations import (
    Citation,
    CitationError,
    QuoteLocation,
    TextVersion,
    locate_quote,
)
from evidhist.settings import Settings


class Health(BaseModel):
    status: str


class LocateQuoteRequest(BaseModel):
    model_config = ConfigDict(strict=True, extra="forbid")

    source: TextVersion
    citation: Citation


def create_app(
    settings: Settings | None = None,
    database: DatabaseProbe | None = None,
    session_factory: async_sessionmaker[AsyncSession] | None = None,
) -> FastAPI:
    """Assemble the app; component tests may inject a probe and a session factory."""
    config = settings if settings is not None else Settings()
    probe = (
        database
        if database is not None
        else PostgresDatabase(config.database_url.get_secret_value())
    )
    engine: AsyncEngine | None = None
    factory: async_sessionmaker[AsyncSession] | None = session_factory
    if factory is None:
        engine = create_engine(config.database_url.get_secret_value())
        factory = create_session_factory(engine)

    @asynccontextmanager
    async def lifespan(_app: FastAPI) -> AsyncGenerator[None]:
        try:
            yield
        finally:
            await probe.close()
            if engine is not None:
                await engine.dispose()

    application = FastAPI(title="EvidHist foundation", version="0.0.1", lifespan=lifespan)
    application.state.session_factory = factory

    @application.exception_handler(RequestValidationError)
    async def validation_handler(_request: Request, exc: RequestValidationError) -> Response:
        """Answer 422 even when the invalid input itself cannot be UTF-8 encoded.

        A request body containing a lone UTF-16 surrogate is rejected by the
        schema, but FastAPI's default handler echoes the input value and then
        fails to encode it; rendering with ``ensure_ascii`` keeps the response
        well-formed.
        """
        body = json_dumps({"detail": exc.errors()}, ensure_ascii=True, default=str)
        return Response(content=body, status_code=422, media_type="application/json")

    @application.get("/health/live", response_model=Health)
    async def liveness() -> Health:
        return Health(status="ok")

    @application.get("/health/ready", response_model=Health)
    async def readiness() -> Health | JSONResponse:
        try:
            await probe.check()
        except SQLAlchemyError:
            return JSONResponse(status_code=503, content={"status": "unavailable"})
        return Health(status="ok")

    @application.post("/v1/quotes/locate", response_model=QuoteLocation)
    async def locate(request: LocateQuoteRequest) -> QuoteLocation:
        """Tool endpoint: validate a citation against explicitly supplied text."""
        try:
            return locate_quote(request.source, request.citation)
        except CitationError as error:
            raise HTTPException(status_code=422, detail={"code": error.code}) from error

    application.include_router(sources_router)
    application.include_router(claims_router)
    return application


app = create_app()
