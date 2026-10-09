import pytest
from fastapi.testclient import TestClient

from evidhist.api import create_app


@pytest.mark.scenario
def test_reprocessing_a_new_version_preserves_the_old_quote_and_rejects_stale_positions() -> None:
    old_citation = {"version_id": "v1", "start": 0, "end": 1, "exact_quote": "春"}
    with TestClient(create_app()) as client:
        old_result = client.post(
            "/v1/quotes/locate",
            json={"source": {"version_id": "v1", "text": "春，甲赴任"}, "citation": old_citation},
        )
        stale_result = client.post(
            "/v1/quotes/locate",
            json={
                "source": {"version_id": "v2", "text": "甲本：春，甲赴任"},
                "citation": old_citation,
            },
        )
        new_result = client.post(
            "/v1/quotes/locate",
            json={
                "source": {"version_id": "v2", "text": "甲本：春，甲赴任"},
                "citation": {"version_id": "v2", "start": 3, "end": 4, "exact_quote": "春"},
            },
        )
        old_again = client.post(
            "/v1/quotes/locate",
            json={"source": {"version_id": "v1", "text": "春，甲赴任"}, "citation": old_citation},
        )

    assert old_result.status_code == new_result.status_code == old_again.status_code == 200
    assert stale_result.json() == {"detail": {"code": "version_mismatch"}}
    assert old_again.json() == old_result.json()
    assert new_result.json()["exact_quote"] == "春"
