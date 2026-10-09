import os
import socket
import subprocess
import sys
import time
from collections.abc import Iterator
from pathlib import Path

import httpx2
import pytest

pytestmark = pytest.mark.system


@pytest.fixture
def live_service(database_url: str, tmp_path: Path) -> Iterator[str]:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        port = sock.getsockname()[1]
    address = f"http://127.0.0.1:{port}"
    environment = os.environ.copy()
    environment["EVIDHIST_DATABASE_URL"] = database_url
    with (tmp_path / "uvicorn.log").open("w") as log:
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
            stdout=log,
            stderr=subprocess.STDOUT,
        )
        try:
            deadline = time.monotonic() + 10
            while time.monotonic() < deadline:
                if process.poll() is not None:
                    pytest.fail("Service exited before startup; see uvicorn.log")
                try:
                    if (
                        httpx2.get(address + "/health/live", timeout=1, trust_env=False).status_code
                        == 200
                    ):
                        break
                except httpx2.HTTPError:
                    time.sleep(0.05)
            else:
                pytest.fail("Service startup timed out; see uvicorn.log")
            yield address
        finally:
            process.terminate()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=5)


def test_running_service_connects_to_postgres_over_real_http(live_service: str) -> None:
    response = httpx2.get(live_service + "/health/ready", timeout=10, trust_env=False)

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_quote_contract_survives_serialization_and_network_transport(live_service: str) -> None:
    response = httpx2.post(
        live_service + "/v1/quotes/locate",
        json={
            "source": {"version_id": "a", "text": "甲𠀀乙"},
            "citation": {"version_id": "a", "start": 1, "end": 2, "exact_quote": "𠀀"},
        },
        timeout=5,
        trust_env=False,
    )

    assert response.status_code == 200
    assert response.json() == {"version_id": "a", "start": 1, "end": 2, "exact_quote": "𠀀"}
