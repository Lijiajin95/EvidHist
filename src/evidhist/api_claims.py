"""HTTP boundary for claims and evidence bindings.

Error codes: ``claim_not_found`` / ``version_not_found`` (404), domain citation
codes ``invalid_range`` / ``quote_mismatch`` (422). Idempotent retries answer
200 with the existing resource. Evidence always records the relation the user
selected; nothing here asserts historical truth.
"""

from datetime import datetime
from typing import Literal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Response
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.ext.asyncio import AsyncSession

from evidhist.claims_service import (
    ClaimSummary,
    EvidenceBinding,
    EvidenceEntry,
    bind_evidence,
    create_claim,
    get_claim,
    list_claims,
)
from evidhist.db import request_session
from evidhist.domain.citations import CitationError
from evidhist.models import ClaimRow
from evidhist.store_errors import NotFoundError

router = APIRouter(prefix="/v1")


class ClaimCreateRequest(BaseModel):
    model_config = ConfigDict(strict=True, extra="forbid")

    statement: str = Field(min_length=1, max_length=500)


class EvidenceBindRequest(BaseModel):
    model_config = ConfigDict(strict=True, extra="forbid")

    version_id: UUID = Field(strict=False)
    start: int = Field(ge=0)
    end: int = Field(ge=0)
    relation: Literal["supports", "contradicts", "mentions", "insufficient"]
    note: str = Field(max_length=500)
    exact_quote: str = Field(min_length=1)


class ClaimOut(BaseModel):
    model_config = ConfigDict(strict=True, extra="forbid")

    id: UUID
    statement: str
    review_status: str
    created_at: datetime


class ClaimCreatedOut(BaseModel):
    model_config = ConfigDict(strict=True, extra="forbid")

    claim: ClaimOut
    created: bool


class EvidenceOut(BaseModel):
    model_config = ConfigDict(strict=True, extra="forbid")

    id: UUID
    claim_id: UUID
    version_id: UUID
    source_id: UUID
    source_title: str
    source_origin: str
    version_label: str
    start: int
    end: int
    quote: str
    relation: str
    note: str
    created_at: datetime


class ClaimDetailOut(BaseModel):
    model_config = ConfigDict(strict=True, extra="forbid")

    claim: ClaimOut
    evidence: list[EvidenceOut]


class ClaimSummaryOut(BaseModel):
    model_config = ConfigDict(strict=True, extra="forbid")

    id: UUID
    statement: str
    review_status: str
    evidence_count: int
    created_at: datetime


class EvidenceCreatedOut(BaseModel):
    model_config = ConfigDict(strict=True, extra="forbid")

    evidence: EvidenceOut
    created: bool


def _claim_out(claim: ClaimRow) -> ClaimOut:
    return ClaimOut(
        id=claim.id,
        statement=claim.statement,
        review_status=claim.review_status,
        created_at=claim.created_at,
    )


def _evidence_out(entry: EvidenceEntry) -> EvidenceOut:
    return EvidenceOut(
        id=entry.id,
        claim_id=entry.claim_id,
        version_id=entry.version_id,
        source_id=entry.source_id,
        source_title=entry.source_title,
        source_origin=entry.source_origin,
        version_label=entry.version_label,
        start=entry.start,
        end=entry.end,
        quote=entry.quote,
        relation=entry.relation,
        note=entry.note,
        created_at=entry.created_at,
    )


@router.post("/claims", response_model=ClaimCreatedOut, status_code=201)
async def create_claim_endpoint(
    request: ClaimCreateRequest,
    session: AsyncSession = Depends(request_session),
) -> Response:
    """Create a claim; an exact-statement retry returns the stored claim with 200."""
    claim, created = await create_claim(session, request.statement)
    body = ClaimCreatedOut(claim=_claim_out(claim), created=created)
    return JSONResponse(status_code=201 if created else 200, content=body.model_dump(mode="json"))


@router.get("/claims", response_model=list[ClaimSummaryOut])
async def list_claims_endpoint(
    session: AsyncSession = Depends(request_session),
) -> list[ClaimSummaryOut]:
    summaries: list[ClaimSummary] = await list_claims(session)
    return [
        ClaimSummaryOut(
            id=summary.id,
            statement=summary.statement,
            review_status=summary.review_status,
            evidence_count=summary.evidence_count,
            created_at=summary.created_at,
        )
        for summary in summaries
    ]


@router.get("/claims/{claim_id}", response_model=ClaimDetailOut)
async def get_claim_endpoint(
    claim_id: UUID, session: AsyncSession = Depends(request_session)
) -> ClaimDetailOut:
    detail = await get_claim(session, claim_id)
    if detail is None:
        raise HTTPException(status_code=404, detail={"code": "claim_not_found"})
    return ClaimDetailOut(
        claim=_claim_out(detail.claim),
        evidence=[_evidence_out(entry) for entry in detail.evidence],
    )


@router.post("/claims/{claim_id}/evidence", response_model=EvidenceCreatedOut, status_code=201)
async def bind_evidence_endpoint(
    claim_id: UUID,
    request: EvidenceBindRequest,
    session: AsyncSession = Depends(request_session),
) -> Response:
    """Validate the citation against the stored version, then bind it idempotently."""
    try:
        evidence, created = await bind_evidence(
            session,
            EvidenceBinding(
                claim_id=claim_id,
                version_id=request.version_id,
                start=request.start,
                end=request.end,
                relation=request.relation,
                note=request.note,
                exact_quote=request.exact_quote,
            ),
        )
    except NotFoundError as error:
        code = f"{error.resource}_not_found"
        raise HTTPException(status_code=404, detail={"code": code}) from None
    except CitationError as error:
        raise HTTPException(status_code=422, detail={"code": error.code}) from error
    body = EvidenceCreatedOut(evidence=_evidence_out(evidence), created=created)
    return JSONResponse(status_code=201 if created else 200, content=body.model_dump(mode="json"))
