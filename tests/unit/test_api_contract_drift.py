"""Controlled-drift acceptance for the OpenAPI snapshot check.

The contract gate must both accept the current snapshot and reject a controlled
temporary change; these cases run the real script against an isolated copy of the
repository snapshot so the working tree is never mutated.
"""

import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "export_openapi.py"
SNAPSHOT = ROOT / "contracts" / "openapi.json"


def write_snapshot(tmp_path: Path, text: str) -> None:
    (tmp_path / "contracts").mkdir()
    (tmp_path / "contracts" / "openapi.json").write_text(text, encoding="utf-8")


def run_check(cwd: Path) -> subprocess.CompletedProcess[str]:
    environment = {**os.environ, "PYTHONPATH": str(ROOT / "src")}
    return subprocess.run(
        [sys.executable, str(SCRIPT), "--check"],
        cwd=cwd,
        env=environment,
        capture_output=True,
        text=True,
        check=False,
    )


def test_current_snapshot_matches_the_running_schema(tmp_path: Path) -> None:
    write_snapshot(tmp_path, SNAPSHOT.read_text(encoding="utf-8"))

    result = run_check(tmp_path)

    assert result.returncode == 0
    assert "matches" in result.stdout


def test_controlled_drift_is_detected(tmp_path: Path) -> None:
    drifted = SNAPSHOT.read_text(encoding="utf-8").replace('"0.0.1"', '"0.0.2"')
    write_snapshot(tmp_path, drifted)

    result = run_check(tmp_path)

    assert result.returncode == 1
    assert "drift" in result.stdout


def test_missing_snapshot_is_reported_as_drift(tmp_path: Path) -> None:
    result = run_check(tmp_path)

    assert result.returncode == 1
    assert "drift" in result.stdout
