"""Fail when independent line or branch coverage falls below the quality policy minimums.

coverage.py's ``percent_covered`` total mixes statements and branches once branch
coverage is enabled; the policy in ``config/quality-policy.toml`` requires line and
branch coverage to each reach their own minimum, computed from the raw counters in
``coverage json`` output. A missing or malformed report is a failed check.

Changed-line coverage uses diff-cover against the Git baseline (``origin/main``, or
``HEAD~1`` when the baseline equals HEAD, as happens on a push to main), comparing
against ``reports/coverage.xml``. A diff-cover run that produces no report is a failed
check; a diff with no measurable lines (tests or docs only) is explicitly "not
applicable" rather than a silent pass.
"""

import argparse
import json
import re
import subprocess
import sys
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TOTAL_KEYS = ("covered_lines", "num_statements", "covered_branches", "num_branches")


def load_policy(path: Path) -> dict:
    return tomllib.loads(path.read_text(encoding="utf-8"))["coverage"]


def read_totals(path: Path) -> dict:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as error:
        raise ValueError(f"coverage report is unreadable: {error}") from error
    totals = data.get("totals") if isinstance(data, dict) else None
    if not isinstance(totals, dict):
        raise ValueError("coverage report is missing a totals object")
    missing = [key for key in TOTAL_KEYS if type(totals.get(key)) is not int]
    if missing:
        raise ValueError(f"coverage totals are missing integer counters: {missing}")
    return totals


def line_coverage(totals: dict) -> float:
    return totals["covered_lines"] / totals["num_statements"] * 100


def branch_coverage(totals: dict) -> float | None:
    if totals["num_branches"] == 0:
        return None
    return totals["covered_branches"] / totals["num_branches"] * 100


def _rev_parse(root: Path, revision: str) -> str | None:
    result = subprocess.run(
        ["git", "rev-parse", "--verify", "--end-of-options", f"{revision}^{{commit}}"],
        cwd=root,
        capture_output=True,
        text=True,
        check=False,
    )
    revision = result.stdout.strip() if result.returncode == 0 else ""
    return revision if re.fullmatch(r"[a-f0-9]{40}|[a-f0-9]{64}", revision) else None


def git_base_revision(root: Path, base: str = "origin/main") -> str | None:
    """基线 revision；origin/main 与 HEAD 相同时回退到 HEAD~1，避免门槛空转。"""
    revision = _rev_parse(root, base)
    if revision is None:
        return None
    if revision == _rev_parse(root, "HEAD"):
        return _rev_parse(root, "HEAD~1")
    return revision


def run_diff_cover(root: Path, base: str, coverage_xml: Path) -> dict | None:
    """用 diff-cover 比较 coverage.xml 与基线，返回 JSON 报告；无法产出时报 None。"""
    report = root / "reports" / "diff-cover.json"
    report.parent.mkdir(parents=True, exist_ok=True)
    result = subprocess.run(
        [
            str(root / ".venv" / "bin" / "diff-cover"),
            str(coverage_xml),
            "--compare-branch",
            base,
            "--json-report",
            str(report),
        ],
        cwd=root,
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0 and not report.exists():
        return None
    try:
        payload = json.loads(report.read_text(encoding="utf-8"))
    except OSError, ValueError:
        return None
    return payload if isinstance(payload, dict) else None


def changed_line_gate(root: Path, minimum: float, coverage_xml: Path) -> dict:
    """改动行覆盖：无基线不适用；有基线必须给出可核对的结果。"""
    base = git_base_revision(root)
    if base is None:
        return {
            "status": "not_applicable",
            "minimum": minimum,
            "reason": "no Git baseline; changed-line coverage cannot be measured yet",
        }
    report = run_diff_cover(root, base, coverage_xml)
    if report is None:
        return {
            "status": "failed",
            "minimum": minimum,
            "base": base,
            "reason": "diff-cover produced no report; changed-line coverage is unverified",
        }
    total, percent = report.get("total_num_lines"), report.get("total_percent_covered")
    if not isinstance(total, int) or total == 0 or not isinstance(percent, int | float):
        return {
            "status": "not_applicable",
            "minimum": minimum,
            "base": base,
            "reason": "the diff has no measurable lines (tests or docs only)",
        }
    measured = float(percent)
    result = {"status": "measured", "minimum": minimum, "base": base, "percent": measured}
    if measured < minimum:
        result["reason"] = f"changed-line coverage {measured:.1f}% is below {minimum}%"
    return result


def run_thresholds(
    report_path: Path, coverage_policy: dict, root: Path, coverage_xml: Path | None = None
) -> dict:
    failures: list[str] = []
    try:
        totals = read_totals(report_path)
        line_percent = line_coverage(totals)
        branch_percent = branch_coverage(totals)
        if line_percent < coverage_policy["line_min"]:
            failures.append(
                f"line coverage {line_percent:.1f}% is below {coverage_policy['line_min']}%"
            )
        branch = {
            "percent": branch_percent,
            "status": "measured",
            "minimum": coverage_policy["branch_min"],
        }
        if branch_percent is None:
            branch["status"] = "not_applicable"
        elif branch_percent < coverage_policy["branch_min"]:
            failures.append(
                f"branch coverage {branch_percent:.1f}% is below {coverage_policy['branch_min']}%"
            )
    except ValueError as error:
        failures.append(str(error))
        line_percent, branch = None, {"percent": None, "status": "missing", "minimum": None}
    changed = changed_line_gate(
        root, coverage_policy["changed_line_min"], coverage_xml or report_path.with_suffix(".xml")
    )
    if "reason" in changed and changed["status"] in {"failed", "measured"}:
        failures.append("changed-line coverage: " + changed["reason"])
    return {
        "report": str(report_path),
        "line": {"percent": line_percent, "minimum": coverage_policy["line_min"]},
        "branch": branch,
        "changed_lines": changed,
        "summary": {"failures": failures, "passed": not failures},
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--report", type=Path, default=ROOT / "reports/coverage.json")
    parser.add_argument("--config", type=Path, default=ROOT / "config/quality-policy.toml")
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument(
        "--json-output", type=Path, default=ROOT / "reports/coverage-thresholds.json"
    )
    args = parser.parse_args()
    result = run_thresholds(
        args.report.resolve(),
        load_policy(args.config.resolve()),
        args.root.resolve(),
        args.report.resolve().with_suffix(".xml"),
    )
    args.json_output.parent.mkdir(parents=True, exist_ok=True)
    args.json_output.write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    for failure in result["summary"]["failures"]:
        print(f"FAIL: {failure}")
    status = "passed" if result["summary"]["passed"] else "failed"
    print(
        f"Coverage thresholds: {status} "
        f"(line {result['line']['percent']}, branch {result['branch']['percent']}, "
        f"changed-lines {result['changed_lines']['status']}"
        f"{' ' + format(result['changed_lines']['percent'], '.1f') + '%' if 'percent' in result['changed_lines'] else ''})."
    )
    return 0 if result["summary"]["passed"] else 1


if __name__ == "__main__":
    sys.exit(main())
