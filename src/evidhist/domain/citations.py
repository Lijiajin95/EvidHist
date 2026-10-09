"""Locate an exact quote in supplied versioned text; this does not assess historical truth."""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class TextVersion(BaseModel):
    model_config = ConfigDict(strict=True, extra="forbid", frozen=True)

    version_id: str = Field(min_length=1, max_length=128)
    text: str = Field(min_length=1)


class Citation(BaseModel):
    model_config = ConfigDict(strict=True, extra="forbid", frozen=True)

    version_id: str = Field(min_length=1, max_length=128)
    start: int = Field(ge=0)
    end: int = Field(ge=0)
    exact_quote: str = Field(min_length=1)


class QuoteLocation(Citation):
    """Offsets count Unicode code points and use an exclusive end."""


class CitationError(ValueError):
    """A stable reason code available both as an attribute and the exception message."""

    def __init__(
        self, code: Literal["version_mismatch", "invalid_range", "quote_mismatch"]
    ) -> None:
        self.code = code
        super().__init__(code)


def locate_quote(source: TextVersion, citation: Citation) -> QuoteLocation:
    """Reject wrong versions, invalid ranges and words that differ from the supplied text."""
    if source.version_id != citation.version_id:
        raise CitationError("version_mismatch")
    if not 0 <= citation.start < citation.end <= len(source.text):
        raise CitationError("invalid_range")
    quote = source.text[citation.start : citation.end]
    if quote != citation.exact_quote:
        raise CitationError("quote_mismatch")
    return QuoteLocation(
        version_id=source.version_id,
        start=citation.start,
        end=citation.end,
        exact_quote=quote,
    )
