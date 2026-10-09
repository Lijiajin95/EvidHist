import pytest
from pydantic import ValidationError

from evidhist.domain.citations import Citation, CitationError, TextVersion, locate_quote


def test_reader_can_locate_quote_in_the_exact_text_version() -> None:
    source = TextVersion(version_id="edition-a", text="甲本：春，甲赴任。")
    citation = Citation(version_id="edition-a", start=3, end=8, exact_quote="春，甲赴任")

    result = locate_quote(source, citation)

    assert result.exact_quote == "春，甲赴任"
    assert result.version_id == "edition-a"
    assert (result.start, result.end) == (3, 8)


def test_matching_words_from_another_version_are_rejected() -> None:
    source = TextVersion(version_id="edition-a", text="甲赴任")
    citation = Citation(version_id="edition-b", start=0, end=3, exact_quote="甲赴任")

    with pytest.raises(CitationError, match=r"^version_mismatch$") as caught:
        locate_quote(source, citation)

    assert caught.value.code == "version_mismatch"


@pytest.mark.parametrize("start,end", [(0, 0), (2, 1), (0, 4), (3, 4)])
def test_invalid_ranges_are_rejected_without_silently_truncating(start: int, end: int) -> None:
    source = TextVersion(version_id="a", text="甲赴任")
    citation = Citation(version_id="a", start=start, end=end, exact_quote="甲")

    with pytest.raises(CitationError) as caught:
        locate_quote(source, citation)

    assert caught.value.code == "invalid_range"


def test_a_real_location_cannot_be_attached_to_different_words() -> None:
    source = TextVersion(version_id="a", text="春，甲赴任")
    citation = Citation(version_id="a", start=0, end=1, exact_quote="秋")

    with pytest.raises(CitationError) as caught:
        locate_quote(source, citation)

    assert caught.value.code == "quote_mismatch"


def test_unicode_positions_use_code_points_and_an_exclusive_end() -> None:
    source = TextVersion(version_id="a", text="甲𠀀乙")
    citation = Citation(version_id="a", start=1, end=2, exact_quote="𠀀")

    result = locate_quote(source, citation)

    assert result.exact_quote == "𠀀"


@pytest.mark.parametrize("bad_start", [-1, True, "0"])
def test_schema_rejects_negative_boolean_or_coerced_positions(bad_start: object) -> None:
    with pytest.raises(ValidationError):
        Citation.model_validate(
            {"version_id": "a", "start": bad_start, "end": 1, "exact_quote": "甲"}
        )


def test_schema_rejects_unknown_fields_and_blank_quotes() -> None:
    with pytest.raises(ValidationError):
        Citation.model_validate(
            {"version_id": "a", "start": 0, "end": 1, "exact_quote": "甲", "approved": True}
        )
    with pytest.raises(ValidationError):
        Citation(version_id="a", start=0, end=1, exact_quote="")
