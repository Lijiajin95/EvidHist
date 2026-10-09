"""SQLAlchemy models for the v0.1 business schema (see migrations/0001_init.sql)."""

import uuid
from datetime import UTC, datetime

from sqlalchemy import DateTime, ForeignKey, Text, UniqueConstraint
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


def utc_now() -> datetime:
    return datetime.now(UTC)


class Base(DeclarativeBase):
    pass


class SourceRow(Base):
    __tablename__ = "sources"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    title: Mapped[str] = mapped_column(Text)
    origin: Mapped[str] = mapped_column(Text, default="")
    usage_terms: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


class TextVersionRow(Base):
    __tablename__ = "text_versions"
    __table_args__ = (
        UniqueConstraint("source_id", "content_sha256", name="text_versions_source_content_unique"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    source_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("sources.id"))
    label: Mapped[str] = mapped_column(Text, default="")
    content: Mapped[str] = mapped_column(Text)
    content_sha256: Mapped[str]
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


class ClaimRow(Base):
    __tablename__ = "claims"
    __table_args__ = (UniqueConstraint("statement", name="claims_statement_unique"),)

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    statement: Mapped[str] = mapped_column(Text)
    review_status: Mapped[str] = mapped_column(Text, default="unverified")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


class EvidenceRow(Base):
    __tablename__ = "evidence"
    __table_args__ = (
        UniqueConstraint(
            "claim_id",
            "version_id",
            "start",
            "end",
            "relation",
            "note",
            name="evidence_natural_key_unique",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    claim_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("claims.id"))
    version_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("text_versions.id"))
    start: Mapped[int]
    end: Mapped[int]
    relation: Mapped[str]
    note: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
