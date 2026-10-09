"""HTTP acceptance for the v0.1 business API over the real PostgreSQL.

Covers the night-goal matrix through the public interface: idempotent creation
(201 then 200), 404 codes for missing sources/versions/claims, 422 domain
citation codes, persisted-version locate including astral characters, and
evidence binding with relation validation.
"""

import uuid

import pytest
import pytest_asyncio
from fastapi.testclient import TestClient
from pydantic import SecretStr

from evidhist.api import create_app
from evidhist.db import create_engine, create_session_factory
from evidhist.db_migrations import apply_migrations
from evidhist.models import ClaimRow, EvidenceRow, SourceRow, TextVersionRow
from evidhist.settings import Settings

pytestmark = pytest.mark.integration


@pytest_asyncio.fixture
async def client(database_url: str):
    engine = create_engine(database_url)
    await apply_migrations(engine)
    factory = create_session_factory(engine)
    async with factory() as session:
        from sqlalchemy import delete

        for table in (EvidenceRow, ClaimRow, TextVersionRow, SourceRow):
            await session.execute(delete(table))
        await session.commit()
    application = create_app(
        settings=Settings(database_url=SecretStr(database_url)), session_factory=factory
    )
    with TestClient(application) as test_client:
        yield test_client
    await engine.dispose()


SOURCE_PAYLOAD = {
    "title": "史記·秦始皇本紀（合成整理本）",
    "origin": "合成材料，用於演示",
    "usage_terms": "合成材料，僅演示用途",
    "initial_text": "帝曰：甲𠀀乙，命有司封禪。",
    "initial_label": "整理初稿",
}


def create_source(client: TestClient, **overrides) -> dict:
    payload = {**SOURCE_PAYLOAD, **overrides}
    response = client.post("/v1/sources", json=payload)
    assert response.status_code == 201, response.text
    return response.json()


def test_source_creation_is_idempotent_with_201_then_200(client: TestClient) -> None:
    first = client.post("/v1/sources", json=SOURCE_PAYLOAD)
    retry = client.post("/v1/sources", json=SOURCE_PAYLOAD)

    assert first.status_code == 201
    assert retry.status_code == 200
    assert first.json()["created"] is True
    assert retry.json()["created"] is False
    assert retry.json()["source"]["id"] == first.json()["source"]["id"]
    assert retry.json()["version"]["id"] == first.json()["version"]["id"]
    listing = client.get("/v1/sources")
    assert [item["title"] for item in listing.json()] == [SOURCE_PAYLOAD["title"]]


def test_source_detail_and_version_content_round_trip(client: TestClient) -> None:
    created = create_source(client)
    source_id = created["source"]["id"]
    version_id = created["version"]["id"]

    detail = client.get(f"/v1/sources/{source_id}")
    version = client.get(f"/v1/versions/{version_id}")

    assert detail.status_code == 200
    assert detail.json()["source"]["usage_terms"] == SOURCE_PAYLOAD["usage_terms"]
    assert [v["id"] for v in detail.json()["versions"]] == [version_id]
    assert version.json()["content"] == SOURCE_PAYLOAD["initial_text"]
    assert version.json()["content_sha256"] == created["version"]["content_sha256"]


def test_missing_sources_and_versions_return_stable_404_codes(client: TestClient) -> None:
    absent = uuid.uuid4()

    assert client.get(f"/v1/sources/{absent}").json() == {"detail": {"code": "source_not_found"}}
    assert client.get(f"/v1/versions/{absent}").json() == {"detail": {"code": "version_not_found"}}
    response = client.post(
        f"/v1/versions/{absent}/locate",
        json={"start": 0, "end": 1, "exact_quote": "甲"},
    )
    assert response.status_code == 404
    assert response.json() == {"detail": {"code": "version_not_found"}}


def test_locate_persisted_version_validates_offsets_and_quote(client: TestClient) -> None:
    version_id = create_source(client)["version"]["id"]

    located = client.post(
        f"/v1/versions/{version_id}/locate",
        json={"start": 4, "end": 5, "exact_quote": "𠀀"},
    )
    backwards = client.post(
        f"/v1/versions/{version_id}/locate",
        json={"start": 5, "end": 4, "exact_quote": "𠀀"},
    )
    mismatch = client.post(
        f"/v1/versions/{version_id}/locate",
        json={"start": 4, "end": 5, "exact_quote": "甲"},
    )

    assert located.status_code == 200
    assert located.json() == {"version_id": version_id, "start": 4, "end": 5, "exact_quote": "𠀀"}
    assert backwards.status_code == 422
    assert backwards.json() == {"detail": {"code": "invalid_range"}}
    assert mismatch.status_code == 422
    assert mismatch.json() == {"detail": {"code": "quote_mismatch"}}


def test_adding_versions_dedupes_and_old_versions_stay_queryable(client: TestClient) -> None:
    created = create_source(client)
    source_id = created["source"]["id"]
    first_version_id = created["version"]["id"]

    added = client.post(
        f"/v1/sources/{source_id}/versions",
        json={"label": "校訂二稿", "text": "帝曰：甲𠀀乙，命有司封禪。補一句。"},
    )
    retry = client.post(
        f"/v1/sources/{source_id}/versions",
        json={"label": "重試", "text": "帝曰：甲𠀀乙，命有司封禪。補一句。"},
    )

    assert added.status_code == 201
    assert retry.status_code == 200
    assert retry.json()["id"] == added.json()["id"]
    old = client.get(f"/v1/versions/{first_version_id}")
    assert old.json()["content"] == SOURCE_PAYLOAD["initial_text"]
    detail = client.get(f"/v1/sources/{source_id}")
    assert len(detail.json()["versions"]) == 2


def test_claim_and_evidence_flow_with_idempotency_and_error_codes(client: TestClient) -> None:
    version_id = create_source(client)["version"]["id"]
    claim = client.post("/v1/claims", json={"statement": "始皇曾東巡封禪。"})
    claim_retry = client.post("/v1/claims", json={"statement": "始皇曾東巡封禪。"})

    assert claim.status_code == 201 and claim_retry.status_code == 200
    claim_id = claim.json()["claim"]["id"]
    binding = {
        "version_id": version_id,
        "start": 4,
        "end": 5,
        "relation": "supports",
        "note": "本紀明載",
        "exact_quote": "𠀀",
    }
    evidence = client.post(f"/v1/claims/{claim_id}/evidence", json=binding)
    evidence_retry = client.post(f"/v1/claims/{claim_id}/evidence", json=binding)

    assert evidence.status_code == 201
    assert evidence_retry.status_code == 200
    assert evidence_retry.json()["evidence"]["id"] == evidence.json()["evidence"]["id"]

    bad_range = client.post(
        f"/v1/claims/{claim_id}/evidence",
        json={**binding, "start": 99, "end": 100, "exact_quote": "甲"},
    )
    missing_claim = client.post(f"/v1/claims/{uuid.uuid4()}/evidence", json=binding)
    bad_relation = client.post(
        f"/v1/claims/{claim_id}/evidence",
        json={**binding, "relation": "proves"},
    )

    assert bad_range.status_code == 422
    assert bad_range.json() == {"detail": {"code": "invalid_range"}}
    assert missing_claim.status_code == 404
    assert missing_claim.json() == {"detail": {"code": "claim_not_found"}}
    assert bad_relation.status_code == 422

    detail = client.get(f"/v1/claims/{claim_id}")
    assert detail.status_code == 200
    entry = detail.json()["evidence"][0]
    assert entry["quote"] == "𠀀"
    assert entry["source_title"] == SOURCE_PAYLOAD["title"]
    assert entry["relation"] == "supports"
    assert client.get("/v1/claims").json()[0]["evidence_count"] == 1


def test_claim_detail_missing_returns_404(client: TestClient) -> None:
    assert client.get(f"/v1/claims/{uuid.uuid4()}").json() == {
        "detail": {"code": "claim_not_found"}
    }


def test_source_list_filters_by_title_query(client: TestClient) -> None:
    create_source(client)
    create_source(
        client,
        title="漢書·高帝紀（合成整理本）",
        origin="合成材料，用於演示",
        initial_text="高祖，沛豐邑中陽里人。",
    )

    filtered = client.get("/v1/sources", params={"q": "漢書"})

    assert [item["title"] for item in filtered.json()] == ["漢書·高帝紀（合成整理本）"]


def test_adding_a_version_to_a_missing_source_returns_404(client: TestClient) -> None:
    response = client.post(
        f"/v1/sources/{uuid.uuid4()}/versions",
        json={"label": "任何版本", "text": "任何文本。"},
    )

    assert response.status_code == 404
    assert response.json() == {"detail": {"code": "source_not_found"}}


def test_binding_evidence_to_a_missing_version_returns_404(client: TestClient) -> None:
    claim = client.post("/v1/claims", json={"statement": "引证不存在版本的論斷。"})
    claim_id = claim.json()["claim"]["id"]

    response = client.post(
        f"/v1/claims/{claim_id}/evidence",
        json={
            "version_id": str(uuid.uuid4()),
            "start": 0,
            "end": 1,
            "relation": "supports",
            "note": "",
            "exact_quote": "甲",
        },
    )

    assert response.status_code == 404
    assert response.json() == {"detail": {"code": "version_not_found"}}
