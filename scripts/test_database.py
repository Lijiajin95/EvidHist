"""Start/stop only the labeled, disposable EvidHist database; Compose is not required."""

import argparse
import json
import os
import subprocess
import time
from pathlib import Path
from typing import Any

# Development tooling script: pyyaml belongs in the dev dependency group by design.
import yaml  # deptry: ignore[DEP004]

NAME = "evidhist-foundation-postgres"
LABEL = "org.evidhist.test-suite"
OWNER = "foundation"


def docker(*arguments: str, check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(["docker", *arguments], check=check, text=True, capture_output=True)


def owned_container() -> dict[str, Any] | None:
    result = docker("container", "inspect", NAME, check=False)
    if result.returncode:
        # A daemon error must not be confused with an absent container.
        docker("info", "--format", "{{.ServerVersion}}")
        if "No such" not in result.stderr:
            raise RuntimeError(result.stderr.strip())
        return None
    container = json.loads(result.stdout)[0]
    if container["Config"]["Labels"].get(LABEL) != OWNER:
        raise RuntimeError("Refusing to modify a container without this project's test label")
    return container


def start_container() -> None:
    manifest = yaml.safe_load(Path("compose.test.yml").read_text())
    image = manifest["services"]["postgres"]["image"]
    port = int(os.environ.get("EVIDHIST_TEST_PORT", "55432"))
    if not 1 <= port <= 65535:
        raise ValueError("Invalid test database port")
    docker(
        "run",
        "--detach",
        "--rm",
        "--name",
        NAME,
        "--label",
        f"{LABEL}={OWNER}",
        "--env",
        "POSTGRES_USER=evidhist",
        "--env",
        "POSTGRES_PASSWORD=evidhist",
        "--env",
        "POSTGRES_DB=evidhist_test",
        "--publish",
        f"127.0.0.1:{port}:5432",
        "--tmpfs",
        "/var/lib/postgresql",
        "--health-cmd",
        "pg_isready -U evidhist -d evidhist_test",
        "--health-interval",
        "1s",
        "--health-timeout",
        "5s",
        "--health-retries",
        "30",
        image,
    )


def wait_until_healthy() -> None:
    deadline = time.monotonic() + 40
    while time.monotonic() < deadline:
        container = owned_container()
        if (
            container is not None
            and container["State"].get("Health", {}).get("Status") == "healthy"
        ):
            print("EvidHist isolated test database is healthy.")
            return
        time.sleep(0.25)
    raise RuntimeError(
        "Test database did not become healthy; inspect its logs and run make db-down"
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=["up", "down"])
    action = parser.parse_args().action
    container = owned_container()
    if action == "down":
        if container is not None:
            docker("rm", "--force", NAME)
        print("EvidHist test database stopped.")
        return
    if container is None:
        start_container()
    wait_until_healthy()


if __name__ == "__main__":
    main()
