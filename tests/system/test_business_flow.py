"""End-to-end business flow over a real uvicorn service and PostgreSQL.

The flow exercises the product path through real HTTP: create a source with its
initial version, bind evidence that cites the persisted version (including an
astral character), then stop the service, start a brand-new process on a fresh
port and read everything back. Persistence across a service restart is the
user-visible guarantee under test.
"""

import asyncio
import os
import socket
import subprocess
import sys
import time
import uuid
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

import httpx2
import pytest

from evidhist.db import create_engine
from evidhist.db_migrations import apply_migrations

pytestmark = pytest.mark.system


def run_migrations(database_url: str) -> None:
    engine = create_engine(database_url)

    async def migrate() -> None:
        await apply_migrations(engine)
        await engine.dispose()

    asyncio.run(migrate())


def _wait_until_live(address: str, process: subprocess.Popen, log: Path) -> None:
    deadline = time.monotonic() + 10
    while time.monotonic() < deadline:
        if process.poll() is not None:
            pytest.fail(f"Service exited before startup; see {log}")
        try:
            response = httpx2.get(address + "/health/live", timeout=1, trust_env=False)
            if response.status_code == 200:
                return
        except httpx2.HTTPError:
            time.sleep(0.05)
    pytest.fail(f"Service startup timed out; see {log}")


@contextmanager
def running_service(database_url: str, tmp_path: Path, log_name: str) -> Iterator[str]:
    """Start one uvicorn process on a free port and yield its address."""
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        port = sock.getsockname()[1]
    address = f"http://127.0.0.1:{port}"
    environment = {**os.environ, "EVIDHIST_DATABASE_URL": database_url}
    log = tmp_path / log_name
    with log.open("w") as stream:
        process = subprocess.Popen(
            [
                sys.executable,
                "-m",
                "uvicorn",
                "evidhist.api:app",
                "--host",
                "127.0.0.1",
                "--port",
                str(port),
            ],
            env=environment,
            stdout=stream,
            stderr=subprocess.STDOUT,
        )
        try:
            _wait_until_live(address, process, log)
            yield address
        finally:
            process.terminate()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=5)


def _create_business_data(service: str, marker: str) -> tuple[str, str, str]:
    """Create a source, a claim and one evidence binding through real HTTP."""
    source_payload = {
        "title": f"史記·秦始皇本紀（合成 {marker}）",
        "origin": "合成材料，用於演示",
        "usage_terms": "合成材料，僅演示用途",
        "initial_text": "帝曰：甲𠀀乙，命有司封禪。",
        "initial_label": "整理初稿",
    }
    created = httpx2.post(service + "/v1/sources", json=source_payload, timeout=10, trust_env=False)
    assert created.status_code == 201, created.text
    version_id = created.json()["version"]["id"]

    located = httpx2.post(
        f"{service}/v1/versions/{version_id}/locate",
        json={"start": 4, "end": 5, "exact_quote": "𠀀"},
        timeout=10,
        trust_env=False,
    )
    assert located.status_code == 200
    assert located.json()["exact_quote"] == "𠀀"

    claim = httpx2.post(
        service + "/v1/claims",
        json={"statement": f"始皇曾東巡封禪（{marker}）。"},
        timeout=10,
        trust_env=False,
    )
    assert claim.status_code == 201, claim.text
    claim_id = claim.json()["claim"]["id"]

    evidence = httpx2.post(
        f"{service}/v1/claims/{claim_id}/evidence",
        json={
            "version_id": version_id,
            "start": 4,
            "end": 5,
            "relation": "supports",
            "note": "本紀明載",
            "exact_quote": "𠀀",
        },
        timeout=10,
        trust_env=False,
    )
    assert evidence.status_code == 201, evidence.text
    return claim_id, version_id, source_payload["title"]


def test_business_flow_persists_across_a_service_restart(database_url: str, tmp_path: Path) -> None:
    run_migrations(database_url)
    marker = uuid.uuid4().hex[:8]
    with running_service(database_url, tmp_path, "first-service.log") as first:
        claim_id, version_id, source_title = _create_business_data(first, marker)

    with running_service(database_url, tmp_path, "second-service.log") as second:
        detail = httpx2.get(f"{second}/v1/claims/{claim_id}", timeout=10, trust_env=False)
        version = httpx2.get(f"{second}/v1/versions/{version_id}", timeout=10, trust_env=False)

    assert detail.status_code == 200
    entries = detail.json()["evidence"]
    assert len(entries) == 1
    assert entries[0]["quote"] == "𠀀"
    assert entries[0]["relation"] == "supports"
    assert entries[0]["source_title"] == source_title
    assert version.status_code == 200
    assert version.json()["content"] == "帝曰：甲𠀀乙，命有司封禪。"


def test_idempotent_retries_over_real_http_do_not_duplicate_rows(
    database_url: str, tmp_path: Path
) -> None:
    run_migrations(database_url)
    marker = uuid.uuid4().hex[:8]
    payload = {
        "title": f"漢書·高帝紀（合成 {marker}）",
        "origin": "合成材料，用於演示",
        "usage_terms": "合成材料，僅演示用途",
        "initial_text": "高祖，沛豐邑中陽里人。",
        "initial_label": "整理初稿",
    }
    with running_service(database_url, tmp_path, "retry-service.log") as service:
        first = httpx2.post(service + "/v1/sources", json=payload, timeout=10, trust_env=False)
        retry = httpx2.post(service + "/v1/sources", json=payload, timeout=10, trust_env=False)
        listing = httpx2.get(service + "/v1/sources", timeout=10, trust_env=False)

    assert first.status_code == 201 and retry.status_code == 200
    assert retry.json()["source"]["id"] == first.json()["source"]["id"]
    matching = [item for item in listing.json() if marker in item["title"]]
    assert len(matching) == 1
