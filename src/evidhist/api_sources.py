"""HTTP boundary for sources, immutable text versions and persisted citation checks.

Error codes are stable: ``source_not_found`` / ``version_not_found`` (404) and
the domain citation codes ``invalid_range`` / ``quote_mismatch`` (422).
Idempotent retries answer 200 with the existing resource instead of 201.
"""

from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.ext.asyncio import AsyncSession

from evidhist.db import request_session
from evidhist.domain.citations import CitationError
from evidhist.models import SourceRow, TextVersionRow
from evidhist.sources_service import (
    NewSource,
    add_version,
    create_source,
    get_source,
    get_version,
    list_sources,
    locate_version,
)
from evidhist.store_errors import NotFoundError

router = APIRouter(prefix="/v1")


class SourceCreateRequest(BaseModel):
    model_config = ConfigDict(strict=True, extra="forbid")

    title: str = Field(min_length=1, max_length=200)
    origin: str = Field(max_length=500)
    usage_terms: str = Field(max_length=500)
    initial_text: str = Field(min_length=1)
    initial_label: str = Field(max_length=100)


class VersionCreateRequest(BaseModel):
    model_config = ConfigDict(strict=True, extra="forbid")

    label: str = Field(max_length=100)
    text: str = Field(min_length=1)


class LocateVersionRequest(BaseModel):
    model_config = ConfigDict(strict=True, extra="forbid")

    start: int = Field(ge=0)
    end: int = Field(ge=0)
    exact_quote: str = Field(min_length=1)


class SourceOut(BaseModel):
    model_config = ConfigDict(strict=True, extra="forbid")

    id: UUID
    title: str
    origin: str
    usage_terms: str
    created_at: datetime
    updated_at: datetime


class VersionOut(BaseModel):
    model_config = ConfigDict(strict=True, extra="forbid")

    id: UUID
    source_id: UUID
    label: str
    content_sha256: str
    created_at: datetime


class VersionContentOut(VersionOut):
    content: str


class SourceWithVersionOut(BaseModel):
    model_config = ConfigDict(strict=True, extra="forbid")

    source: SourceOut
    version: VersionOut
    created: bool


class SourceDetailOut(BaseModel):
    model_config = ConfigDict(strict=True, extra="forbid")

    source: SourceOut
    versions: list[VersionOut]


class SourceSummaryOut(BaseModel):
    model_config = ConfigDict(strict=True, extra="forbid")

    id: UUID
    title: str
    origin: str
    usage_terms: str
    version_count: int
    created_at: datetime


class QuoteLocationOut(BaseModel):
    model_config = ConfigDict(strict=True, extra="forbid")

    version_id: str
    start: int
    end: int
    exact_quote: str


def _source_out(source: SourceRow) -> SourceOut:
    return SourceOut(
        id=source.id,
        title=source.title,
        origin=source.origin,
        usage_terms=source.usage_terms,
        created_at=source.created_at,
        updated_at=source.updated_at,
    )


def _version_out(version: TextVersionRow) -> VersionOut:
    return VersionOut(
        id=version.id,
        source_id=version.source_id,
        label=version.label,
        content_sha256=version.content_sha256,
        created_at=version.created_at,
    )


@router.post(
    "/sources",
    response_model=SourceWithVersionOut,
    status_code=201,
)
async def create_source_endpoint(
    request: SourceCreateRequest,
    session: AsyncSession = Depends(request_session),
) -> Response:
    """Create a material with its first immutable text version; retries return 200."""
    source, version, created = await create_source(
        session,
        NewSource(
            title=request.title,
            origin=request.origin,
            usage_terms=request.usage_terms,
            text=request.initial_text,
            label=request.initial_label,
        ),
    )
    body = SourceWithVersionOut(
        source=_source_out(source), version=_version_out(version), created=created
    )
    return JSONResponse(status_code=201 if created else 200, content=body.model_dump(mode="json"))


@router.get("/sources", response_model=list[SourceSummaryOut])
async def list_sources_endpoint(
    q: str | None = Query(default=None, max_length=100),
    session: AsyncSession = Depends(request_session),
) -> list[SourceSummaryOut]:
    summaries = await list_sources(session, query=q)
    return [
        SourceSummaryOut(
            id=summary.id,
            title=summary.title,
            origin=summary.origin,
            usage_terms=summary.usage_terms,
            version_count=summary.version_count,
            created_at=summary.created_at,
        )
        for summary in summaries
    ]


@router.get("/sources/{source_id}", response_model=SourceDetailOut)
async def get_source_endpoint(
    source_id: UUID, session: AsyncSession = Depends(request_session)
) -> SourceDetailOut:
    detail = await get_source(session, source_id)
    if detail is None:
        raise HTTPException(status_code=404, detail={"code": "source_not_found"})
    return SourceDetailOut(
        source=_source_out(detail.source),
        versions=[_version_out(version) for version in detail.versions],
    )


@router.post("/sources/{source_id}/versions", response_model=VersionOut, status_code=201)
async def add_version_endpoint(
    source_id: UUID,
    request: VersionCreateRequest,
    session: AsyncSession = Depends(request_session),
) -> Response:
    """Add a new immutable version; identical content returns the stored version (200)."""
    try:
        version, created = await add_version(
            session, source_id=source_id, label=request.label, text=request.text
        )
    except NotFoundError:
        raise HTTPException(status_code=404, detail={"code": "source_not_found"}) from None
    body = _version_out(version)
    return JSONResponse(status_code=201 if created else 200, content=body.model_dump(mode="json"))


@router.get("/versions/{version_id}", response_model=VersionContentOut)
async def get_version_endpoint(
    version_id: UUID, session: AsyncSession = Depends(request_session)
) -> VersionContentOut:
    version = await get_version(session, version_id)
    if version is None:
        raise HTTPException(status_code=404, detail={"code": "version_not_found"})
    return VersionContentOut(
        id=version.id,
        source_id=version.source_id,
        label=version.label,
        content=version.content,
        content_sha256=version.content_sha256,
        created_at=version.created_at,
    )


@router.post("/versions/{version_id}/locate", response_model=QuoteLocationOut)
async def locate_version_endpoint(
    version_id: UUID,
    request: LocateVersionRequest,
    session: AsyncSession = Depends(request_session),
) -> QuoteLocationOut:
    """Validate a citation against the persisted version text (the product flow)."""
    try:
        located = await locate_version(
            session,
            version_id=version_id,
            start=request.start,
            end=request.end,
            exact_quote=request.exact_quote,
        )
    except NotFoundError:
        raise HTTPException(status_code=404, detail={"code": "version_not_found"}) from None
    except CitationError as error:
        raise HTTPException(status_code=422, detail={"code": error.code}) from error
    return QuoteLocationOut(
        version_id=located.version_id,
        start=located.start,
        end=located.end,
        exact_quote=located.exact_quote,
    )
