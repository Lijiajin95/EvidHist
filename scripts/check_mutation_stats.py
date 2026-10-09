"""Reject empty, incomplete, surviving or unaccounted mutation results.

The gates come from ``config/quality-policy.toml`` [mutation]: the current mutmut
scope is the critical citation domain, so unreviewed survivors and every incomplete
state (no tests, skipped, suspicious, timeout, segfault, user interrupt) must be
zero, the report must be non-empty, and the counters must account for the total.
``general_killed_min`` is validated for the future general-module scope where the
killed-share denominator is defined in the handoff section 9; it is not applied to
this critical-scope report. A missing or unreadable report is a failed check.
"""

import argparse
import json
import sys
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
COUNTERS = (
    "total",
    "killed",
    "survived",
    "no_tests",
    "skipped",
    "suspicious",
    "timeout",
    "segfault",
    "check_was_interrupted_by_user",
)
INCOMPLETE_COUNTERS = COUNTERS[3:]
POLICY_KEYS = (
    "general_killed_min",
    "critical_unreviewed_survivors_max",
    "unresolved_incomplete_states_max",
    "require_nonempty_report",
)


def load_policy(path: Path) -> dict:
    config = tomllib.loads(path.read_text(encoding="utf-8"))
    return config.get("mutation", {})


def read_stats(path: Path) -> dict:
    try:
        stats = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as error:
        raise ValueError(f"mutation report is missing or unreadable: {error}") from error
    missing = [key for key in COUNTERS if type(stats.get(key)) is not int or stats[key] < 0]
    if missing:
        raise ValueError(f"mutation report is missing valid counters: {missing}")
    return stats


def run_stats_check(stats_path: Path, mutation_policy: dict) -> dict:
    failures: list[str] = []
    missing_keys = [key for key in POLICY_KEYS if key not in mutation_policy]
    if missing_keys:
        failures.append(f"mutation policy is missing keys: {missing_keys}")
    try:
        stats = read_stats(stats_path)
    except ValueError as error:
        failures.append(str(error))
        stats = {key: None for key in COUNTERS}
    else:
        if mutation_policy.get("require_nonempty_report") and stats["total"] == 0:
            failures.append("mutation report is empty; no mutants were generated")
        if stats["survived"] is not None and stats["survived"] > mutation_policy.get(
            "critical_unreviewed_survivors_max", -1
        ):
            failures.append(
                f"{stats['survived']} surviving mutants are unreviewed in the critical scope"
            )
        incomplete = sum(stats[key] or 0 for key in INCOMPLETE_COUNTERS)
        if incomplete > mutation_policy.get("unresolved_incomplete_states_max", -1):
            detail = ", ".join(f"{key}={stats[key]}" for key in INCOMPLETE_COUNTERS if stats[key])
            failures.append(f"{incomplete} mutants are in unresolved incomplete states: {detail}")
        accounted = stats["killed"] + stats["survived"] + incomplete
        if accounted != stats["total"]:
            failures.append(f"counters account for {accounted} of {stats['total']} total mutants")
    return {
        "report": str(stats_path),
        **{key: stats[key] for key in COUNTERS},
        "general_killed_min": mutation_policy.get("general_killed_min"),
        "summary": {"failures": failures, "passed": not failures},
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--stats", type=Path, default=ROOT / "mutants/mutmut-cicd-stats.json")
    parser.add_argument("--config", type=Path, default=ROOT / "config/quality-policy.toml")
    args = parser.parse_args()
    result = run_stats_check(args.stats.resolve(), load_policy(args.config.resolve()))
    for failure in result["summary"]["failures"]:
        print(f"FAIL: {failure}")
    status = "passed" if result["summary"]["passed"] else "failed"
    print(f"Mutation gate {status}: {result['killed']}/{result['total']} killed.")
    return 0 if result["summary"]["passed"] else 1


if __name__ == "__main__":
    sys.exit(main())
