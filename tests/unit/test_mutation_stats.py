"""Mutation-report gates driven by config/quality-policy.toml [mutation].

Every incomplete state (no tests, skipped, suspicious, timeout, segfault, user
interrupt) must be zero for the critical scope, the report must be non-empty, and
the counters must account for the total. Missing reports, malformed JSON and
missing policy keys are failed checks, not passes.
"""

import importlib.util
import json
from pathlib import Path
from types import ModuleType

import pytest

SCRIPT_PATH = Path(__file__).resolve().parents[2] / "scripts" / "check_mutation_stats.py"


@pytest.fixture(scope="module")
def gates() -> ModuleType:
    spec = importlib.util.spec_from_file_location("check_mutation_stats", SCRIPT_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def write_stats(tmp_path: Path, **overrides: int) -> Path:
    counters = {
        "total": 27,
        "killed": 27,
        "survived": 0,
        "no_tests": 0,
        "skipped": 0,
        "suspicious": 0,
        "timeout": 0,
        "segfault": 0,
        "check_was_interrupted_by_user": 0,
        **overrides,
    }
    path = tmp_path / "stats.json"
    path.write_text(json.dumps(counters), encoding="utf-8")
    return path


def toml_value(value: object) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    return str(value)


def write_config(tmp_path: Path, **overrides: object) -> Path:
    values = {
        "general_killed_min": 90,
        "critical_unreviewed_survivors_max": 0,
        "unresolved_incomplete_states_max": 0,
        "require_nonempty_report": True,
        **overrides,
    }
    body = "\n".join(f"{key} = {toml_value(value)}" for key, value in values.items())
    path = tmp_path / "quality-policy.toml"
    path.write_text(f"schema_version = 1\n[mutation]\n{body}\n", encoding="utf-8")
    return path


def run(gates: ModuleType, stats: Path, config: Path) -> dict:
    return gates.run_stats_check(stats, gates.load_policy(config))


def test_fully_killed_nonempty_report_passes(gates: ModuleType, tmp_path: Path) -> None:
    result = run(gates, write_stats(tmp_path), write_config(tmp_path))

    assert result["summary"]["passed"] is True
    assert result["killed"] == 27
    assert result["total"] == 27


@pytest.mark.parametrize(
    "field,value,phrase",
    [
        ("total", 0, "empty"),
        ("survived", 2, "surviving"),
        ("no_tests", 1, "no_tests"),
        ("timeout", 1, "timeout"),
        ("check_was_interrupted_by_user", 1, "check_was_interrupted_by_user"),
        ("segfault", 1, "segfault"),
    ],
)
def test_incomplete_or_surviving_states_fail(
    gates: ModuleType, tmp_path: Path, field: str, value: int, phrase: str
) -> None:
    counters = {"total": 27, "killed": 27 - value} if field != "total" else {}
    result = run(gates, write_stats(tmp_path, **{field: value}, **counters), write_config(tmp_path))

    assert result["summary"]["passed"] is False
    assert any(phrase in failure for failure in result["summary"]["failures"])


def test_counters_that_do_not_account_for_the_total_fail(gates: ModuleType, tmp_path: Path) -> None:
    result = run(gates, write_stats(tmp_path, killed=20), write_config(tmp_path))

    assert result["summary"]["passed"] is False
    assert any("account" in failure for failure in result["summary"]["failures"])


def test_policy_values_are_applied_not_hardcoded(gates: ModuleType, tmp_path: Path) -> None:
    config = write_config(tmp_path, critical_unreviewed_survivors_max=1)
    result = run(gates, write_stats(tmp_path, survived=1, killed=26), config)

    assert result["summary"]["passed"] is True


def test_missing_or_malformed_reports_fail(gates: ModuleType, tmp_path: Path) -> None:
    config = write_config(tmp_path)

    missing = run(gates, tmp_path / "absent.json", config)
    assert missing["summary"]["passed"] is False
    assert any(
        "missing" in failure or "readable" in failure for failure in missing["summary"]["failures"]
    )

    broken = tmp_path / "broken.json"
    broken.write_text("{oops", encoding="utf-8")
    malformed = run(gates, broken, config)
    assert malformed["summary"]["passed"] is False

    incomplete = tmp_path / "incomplete.json"
    incomplete.write_text(json.dumps({"total": 5, "killed": 5}), encoding="utf-8")
    partial = run(gates, incomplete, config)
    assert partial["summary"]["passed"] is False
    assert any("counters" in failure for failure in partial["summary"]["failures"])


def test_missing_policy_keys_fail(gates: ModuleType, tmp_path: Path) -> None:
    config = tmp_path / "policy.toml"
    config.write_text("[mutation]\ncritical_unreviewed_survivors_max = 0\n", encoding="utf-8")

    result = run(gates, write_stats(tmp_path), config)

    assert result["summary"]["passed"] is False
    assert any("missing keys" in failure for failure in result["summary"]["failures"])
