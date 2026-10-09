"""Start/stop the labeled EvidHist demo database with a persistent data volume.

Unlike the tmpfs test database, demo data survives container restarts in the
named volume ``evidhist-demo-data``; removing the data requires an explicit
`docker volume rm`. The container only binds 127.0.0.1:55433.
"""

import argparse
import json
import subprocess
import time
from typing import Any

NAME = "evidhist-demo-postgres"
LABEL = "org.evidhist.test-suite"
OWNER = "demo"
VOLUME = "evidhist-demo-data"


def docker(*arguments: str, check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(["docker", *arguments], check=check, text=True, capture_output=True)


def owned_container() -> dict[str, Any] | None:
    result = docker("container", "inspect", NAME, check=False)
    if result.returncode:
        docker("info", "--format", "{{.ServerVersion}}")
        if "No such" not in result.stderr:
            raise RuntimeError(result.stderr.strip())
        return None
    container = json.loads(result.stdout)[0]
    if container["Config"]["Labels"].get(LABEL) != OWNER:
        raise RuntimeError("Refusing to modify a container without this project's demo label")
    return container


def start_container() -> None:
    docker(
        "run",
        "--detach",
        "--rm",
        "--name",
        NAME,
        "--label",
        f"{LABEL}={OWNER}",
        "-v",
        f"{VOLUME}:/var/lib/postgresql",
        "--env",
        "POSTGRES_USER=evidhist",
        "--env",
        "POSTGRES_PASSWORD=evidhist",
        "--env",
        "POSTGRES_DB=evidhist_demo",
        "--publish",
        "127.0.0.1:55433:5432",
        "--health-cmd",
        "pg_isready -U evidhist -d evidhist_demo",
        "--health-interval",
        "1s",
        "--health-timeout",
        "5s",
        "--health-retries",
        "30",
        "pgvector/pgvector:pg18@sha256:2358fcba361ed2233a5ed81b5fe4ca779ccb304120ce531a3bf51c0ed7e2bc11",
    )


def wait_until_healthy() -> None:
    deadline = time.monotonic() + 60
    while time.monotonic() < deadline:
        current = owned_container()
        if current is not None and current["State"].get("Health", {}).get("Status") == "healthy":
            print("EvidHist demo database is healthy on 127.0.0.1:55433 (persistent volume).")
            return
        time.sleep(0.25)
    raise RuntimeError("Demo database did not become healthy; inspect its logs")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=["up", "down", "status"])
    action = parser.parse_args().action
    container = owned_container()
    if action == "status":
        healthy = (
            bool(container) and container["State"].get("Health", {}).get("Status") == "healthy"
        )
        print("demo database healthy" if healthy else "demo database not running")
        return
    if action == "down":
        if container is not None:
            docker("rm", "--force", NAME)
        print("Demo database stopped (data volume kept).")
        return
    if container is None:
        start_container()
    wait_until_healthy()


if __name__ == "__main__":
    main()
