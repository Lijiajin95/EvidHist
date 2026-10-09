import pytest
from fastapi.testclient import TestClient
from sqlalchemy.exc import SQLAlchemyError

from evidhist.api import create_app


class AvailableDatabase:
    async def check(self) -> None:
        return None

    async def close(self) -> None:
        return None


class UnavailableDatabase(AvailableDatabase):
    async def check(self) -> None:
        raise SQLAlchemyError("private connection details")


def test_live_and_ready_are_distinct_public_contracts() -> None:
    with TestClient(create_app(database=UnavailableDatabase())) as client:
        assert client.get("/health/live").status_code == 200
        response = client.get("/health/ready")

    assert response.status_code == 503
    assert response.json() == {"status": "unavailable"}
    assert "private" not in response.text


def test_ready_succeeds_when_database_boundary_is_available() -> None:
    with TestClient(create_app(database=AvailableDatabase())) as client:
        response = client.get("/health/ready")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_api_returns_the_exact_source_words_and_declared_positions() -> None:
    with TestClient(create_app(database=AvailableDatabase())) as client:
        response = client.post(
            "/v1/quotes/locate",
            json={
                "source": {"version_id": "a", "text": "甲𠀀乙"},
                "citation": {"version_id": "a", "start": 1, "end": 2, "exact_quote": "𠀀"},
            },
        )

    assert response.status_code == 200
    assert response.json() == {"version_id": "a", "start": 1, "end": 2, "exact_quote": "𠀀"}


@pytest.mark.parametrize(
    "start,quote,version,code",
    [
        (0, "秋", "a", "quote_mismatch"),
        (2, "甲", "a", "invalid_range"),
        (0, "甲", "b", "version_mismatch"),
    ],
)
def test_domain_failures_have_stable_api_error_codes(
    start: int, quote: str, version: str, code: str
) -> None:
    with TestClient(create_app(database=AvailableDatabase())) as client:
        response = client.post(
            "/v1/quotes/locate",
            json={
                "source": {"version_id": "a", "text": "甲"},
                "citation": {"version_id": version, "start": start, "end": 1, "exact_quote": quote},
            },
        )

    assert response.status_code == 422
    assert response.json() == {"detail": {"code": code}}


def test_api_schema_rejects_string_offsets_and_extra_fields() -> None:
    with TestClient(create_app(database=AvailableDatabase())) as client:
        response = client.post(
            "/v1/quotes/locate",
            json={
                "source": {"version_id": "a", "text": "甲"},
                "citation": {"version_id": "a", "start": "0", "end": 1, "exact_quote": "甲"},
                "approved": True,
            },
        )

    assert response.status_code == 422
