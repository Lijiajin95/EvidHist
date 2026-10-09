from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from typing import Literal

from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict
from sqlalchemy.exc import SQLAlchemyError

from evidhist.database import DatabaseProbe, PostgresDatabase
from evidhist.domain.citations import (
    Citation,
    CitationError,
    QuoteLocation,
    TextVersion,
    locate_quote,
)
from evidhist.settings import Settings


class Health(BaseModel):
    status: Literal["ok"] = "ok"


class LocateQuoteRequest(BaseModel):
    model_config = ConfigDict(strict=True, extra="forbid")

    source: TextVersion
    citation: Citation


def create_app(settings: Settings | None = None, database: DatabaseProbe | None = None) -> FastAPI:
    config = settings if settings is not None else Settings()
    probe = (
        database
        if database is not None
        else PostgresDatabase(config.database_url.get_secret_value())
    )

    @asynccontextmanager
    async def lifespan(_app: FastAPI) -> AsyncGenerator[None]:
        try:
            yield
        finally:
            await probe.close()

    application = FastAPI(title="EvidHist foundation", version="0.0.1", lifespan=lifespan)

    @application.get("/health/live", response_model=Health)
    async def liveness() -> Health:
        return Health()

    @application.get("/health/ready", response_model=Health)
    async def readiness() -> Health | JSONResponse:
        try:
            await probe.check()
        except SQLAlchemyError:
            return JSONResponse(status_code=503, content={"status": "unavailable"})
        return Health()

    @application.post("/v1/quotes/locate", response_model=QuoteLocation)
    async def locate(request: LocateQuoteRequest) -> QuoteLocation:
        try:
            return locate_quote(request.source, request.citation)
        except CitationError as error:
            raise HTTPException(status_code=422, detail={"code": error.code}) from error

    return application


app = create_app()
