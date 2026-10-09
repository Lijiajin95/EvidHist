import pytest
from hypothesis import given
from hypothesis import strategies as st

from evidhist.domain.citations import Citation, CitationError, TextVersion, locate_quote


@given(prefix=st.text(), quote=st.text(min_size=1), suffix=st.text())
def test_an_inserted_quote_is_locatable_for_arbitrary_unicode(
    prefix: str, quote: str, suffix: str
) -> None:
    source = TextVersion(version_id="a", text=prefix + quote + suffix)
    citation = Citation(
        version_id="a", start=len(prefix), end=len(prefix) + len(quote), exact_quote=quote
    )

    assert locate_quote(source, citation).exact_quote == quote


@given(text=st.text(min_size=1))
def test_same_content_under_a_different_version_never_counts_as_the_requested_version(
    text: str,
) -> None:
    source = TextVersion(version_id="a", text=text)
    citation = Citation(version_id="b", start=0, end=len(text), exact_quote=text)

    with pytest.raises(CitationError, match="version_mismatch"):
        locate_quote(source, citation)


@given(text=st.text(min_size=1), excess=st.integers(min_value=1, max_value=10000))
def test_ranges_past_the_end_cannot_be_accepted_as_truncated_quotes(text: str, excess: int) -> None:
    source = TextVersion(version_id="a", text=text)
    citation = Citation(version_id="a", start=0, end=len(text) + excess, exact_quote=text)

    with pytest.raises(CitationError, match="invalid_range"):
        locate_quote(source, citation)
