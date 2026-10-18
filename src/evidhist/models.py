"""SQLAlchemy models for the business schema (see migrations/*.sql)."""

import uuid
from datetime import UTC, datetime

from sqlalchemy import DateTime, ForeignKey, Integer, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
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


class ConversationRow(Base):
    """一次人机对话；标题默认「新对话」，首条用户消息到达时改写。"""

    __tablename__ = "conversations"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    title: Mapped[str] = mapped_column(Text, default="新对话")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


class MessageRow(Base):
    __tablename__ = "messages"
    __table_args__ = (
        UniqueConstraint("conversation_id", "client_message_id", name="messages_client_id_unique"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    conversation_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("conversations.id", ondelete="CASCADE")
    )
    role: Mapped[str] = mapped_column(Text)
    content: Mapped[str] = mapped_column(Text, default="")
    status: Mapped[str] = mapped_column(Text, default="done")
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    client_message_id: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


class MessageEventRow(Base):
    """消息内的结构化事件（工具调用/结果、引文校验、评审、产物），seq 单调递增。"""

    __tablename__ = "message_events"
    __table_args__ = (UniqueConstraint("message_id", "seq", name="message_events_seq_unique"),)

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    message_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("messages.id", ondelete="CASCADE"))
    seq: Mapped[int] = mapped_column(Integer)
    kind: Mapped[str] = mapped_column(Text)
    payload: Mapped[dict[str, object]] = mapped_column(JSONB, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
