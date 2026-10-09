"""Pure domain rules for materials: content hashing and evidence relations.

The content hash is the identity anchor for immutable text versions and the
natural idempotency key for retries; relations are the closed vocabulary the
workbench uses to express how a citation relates to a claim.
"""

import pytest

from evidhist.domain.materials import (
    RELATIONS,
    content_sha256,
    normalize_relation,
)


def test_content_hash_is_sha256_hex_of_exact_utf8_text() -> None:
    digest = content_sha256("帝曰：甲𠀀乙")

    import hashlib

    assert digest == hashlib.sha256("帝曰：甲𠀀乙".encode()).hexdigest()
    assert len(digest) == 64


def test_content_hash_distinguishes_whitespace_and_case() -> None:
    assert content_sha256("甲乙") != content_sha256("甲 乙")
    assert content_sha256("ABC") != content_sha256("abc")
    assert content_sha256("") == content_sha256("")


def test_relations_form_the_documented_closed_vocabulary() -> None:
    assert set(RELATIONS) == {"supports", "contradicts", "mentions", "insufficient"}


@pytest.mark.parametrize(
    "value,expected",
    [
        ("supports", "supports"),
        ("contradicts", "contradicts"),
        ("mentions", "mentions"),
        ("insufficient", "insufficient"),
    ],
)
def test_normalize_relation_accepts_documented_values(value: str, expected: str) -> None:
    assert normalize_relation(value) == expected


@pytest.mark.parametrize("value", ["", "support", "SUPPORTS", "支持", "unknown", "supports "])
def test_normalize_relation_rejects_undocumented_values(value: str) -> None:
    with pytest.raises(ValueError, match="relation must be one of: supports, "):
        normalize_relation(value)
