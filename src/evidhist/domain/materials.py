"""Pure rules for materials: content hashing and the evidence relation vocabulary."""

import hashlib

RELATIONS = ("supports", "contradicts", "mentions", "insufficient")


def content_sha256(text: str) -> str:
    """Hex SHA-256 of the exact UTF-8 bytes; the identity of a text version."""
    # Codec names are case-insensitive in Python, so casing mutants here are
    # equivalent and cannot change behavior; excluded from mutation on review.
    return hashlib.sha256(text.encode("utf-8")).hexdigest()  # pragma: no mutate


def normalize_relation(value: str) -> str:
    """Accept only the documented relation codes; anything else is a contract error."""
    if value not in RELATIONS:
        allowed = ", ".join(RELATIONS)
        raise ValueError(f"relation must be one of: {allowed}")
    return value
