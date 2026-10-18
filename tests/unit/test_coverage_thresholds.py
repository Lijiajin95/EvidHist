"""Independent line/branch coverage gates from raw coverage.py counts.

The combined ``percent_covered`` figure mixes statements and branches; the quality
policy requires each dimension to reach its own minimum. These cases also pin the
negative example from the handoff: high line coverage with low branch coverage must
fail, and a missing or malformed report is a failed check, never a pass.
"""

import importlib.util
import json
from pathlib import Path
from types import ModuleType

import pytest

SCRIPT_PATH = Path(__file__).resolve().parents[2] / "scripts" / "check_coverage_thresholds.py"


@pytest.fixture(scope="module")
def gates() -> ModuleType:
    spec = importlib.util.spec_from_file_location("check_coverage_thresholds", SCRIPT_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def write_coverage(tmp_path: Path, totals: dict) -> Path:
    report = tmp_path / "coverage.json"
    report.write_text(json.dumps({"meta": {}, "files": {}, "totals": totals}), encoding="utf-8")
    return report


def write_config(tmp_path: Path, **coverage: float) -> Path:
    values = {"line_min": 90, "branch_min": 90, "changed_line_min": 90, **coverage}
    body = "\n".join(f"{key} = {value}" for key, value in values.items())
    path = tmp_path / "quality-policy.toml"
    path.write_text(f"schema_version = 1\n[coverage]\n{body}\n", encoding="utf-8")
    return path


def totals(line: float, branch: float) -> dict:
    statements, branches = 100, 100
    return {
        "covered_lines": round(statements * line / 100),
        "num_statements": statements,
        "covered_branches": round(branches * branch / 100),
        "num_branches": branches,
        "percent_covered": (line + branch) / 2,
    }


def test_both_dimensions_at_or_above_the_minimum_pass(gates: ModuleType, tmp_path: Path) -> None:
    report = write_coverage(tmp_path, totals(90, 90))
    config = write_config(tmp_path)

    result = gates.run_thresholds(report, gates.load_policy(config), tmp_path)

    assert result["summary"]["passed"] is True
    assert result["line"]["percent"] == pytest.approx(90)
    assert result["branch"]["percent"] == pytest.approx(90)


def test_high_line_coverage_with_low_branch_coverage_fails(
    gates: ModuleType, tmp_path: Path
) -> None:
    report = write_coverage(tmp_path, totals(95, 80))
    config = write_config(tmp_path)

    result = gates.run_thresholds(report, gates.load_policy(config), tmp_path)

    assert result["summary"]["passed"] is False
    assert any("branch" in failure for failure in result["summary"]["failures"])
    assert result["line"]["percent"] == pytest.approx(95)


def test_low_line_coverage_fails_even_with_full_branch_coverage(
    gates: ModuleType, tmp_path: Path
) -> None:
    report = write_coverage(tmp_path, totals(85, 100))
    config = write_config(tmp_path)

    result = gates.run_thresholds(report, gates.load_policy(config), tmp_path)

    assert result["summary"]["passed"] is False
    assert any("line" in failure for failure in result["summary"]["failures"])


def test_custom_minimums_from_the_policy_are_applied(gates: ModuleType, tmp_path: Path) -> None:
    report = write_coverage(tmp_path, totals(90, 90))
    config = write_config(tmp_path, line_min=95)

    result = gates.run_thresholds(report, gates.load_policy(config), tmp_path)

    assert result["summary"]["passed"] is False
    assert any("line" in failure for failure in result["summary"]["failures"])


def test_zero_branches_make_the_branch_gate_not_applicable_not_green(
    gates: ModuleType, tmp_path: Path
) -> None:
    report = write_coverage(
        tmp_path,
        {
            "covered_lines": 90,
            "num_statements": 100,
            "covered_branches": 0,
            "num_branches": 0,
            "percent_covered": 90,
        },
    )
    config = write_config(tmp_path)

    result = gates.run_thresholds(report, gates.load_policy(config), tmp_path)

    assert result["summary"]["passed"] is True
    assert result["branch"]["status"] == "not_applicable"
    assert result["branch"]["percent"] is None


def test_missing_or_malformed_reports_fail_the_check(gates: ModuleType, tmp_path: Path) -> None:
    config = write_config(tmp_path)

    missing = gates.run_thresholds(tmp_path / "absent.json", gates.load_policy(config), tmp_path)
    assert missing["summary"]["passed"] is False
    assert any("missing" in failure for failure in missing["summary"]["failures"])

    malformed = tmp_path / "broken.json"
    malformed.write_text("{not json", encoding="utf-8")
    broken = gates.run_thresholds(malformed, gates.load_policy(config), tmp_path)
    assert broken["summary"]["passed"] is False

    incomplete = write_coverage(tmp_path, {"covered_lines": 90})
    partial = gates.run_thresholds(incomplete, gates.load_policy(config), tmp_path)
    assert partial["summary"]["passed"] is False


def test_changed_line_coverage_is_not_applicable_without_a_git_baseline(
    gates: ModuleType, tmp_path: Path
) -> None:
    report = write_coverage(tmp_path, totals(90, 90))
    config = write_config(tmp_path)

    result = gates.run_thresholds(report, gates.load_policy(config), tmp_path)

    assert result["changed_lines"]["status"] == "not_applicable"
    assert result["summary"]["passed"] is True


def diff_report(total_lines: int, percent: float | None) -> dict:
    return {
        "total_num_lines": total_lines,
        "total_percent_covered": percent,
        "num_changed_lines": total_lines,
    }


def test_changed_lines_are_measured_against_the_git_baseline(
    gates: ModuleType, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    report = write_coverage(tmp_path, totals(90, 90))
    config = write_config(tmp_path)
    monkeypatch.setattr(gates, "git_base_revision", lambda root: "b" * 40)
    monkeypatch.setattr(gates, "run_diff_cover", lambda *args, **kwargs: diff_report(20, 95.0))

    result = gates.run_thresholds(report, gates.load_policy(config), tmp_path)

    assert result["changed_lines"]["status"] == "measured"
    assert result["changed_lines"]["percent"] == 95.0
    assert result["changed_lines"]["base"] == "b" * 40
    assert result["summary"]["passed"] is True


def test_changed_lines_below_the_minimum_fail_the_check(
    gates: ModuleType, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    report = write_coverage(tmp_path, totals(95, 95))
    config = write_config(tmp_path)
    monkeypatch.setattr(gates, "git_base_revision", lambda root: "c" * 40)
    monkeypatch.setattr(gates, "run_diff_cover", lambda *args, **kwargs: diff_report(20, 40.0))

    result = gates.run_thresholds(report, gates.load_policy(config), tmp_path)

    assert result["changed_lines"]["status"] == "measured"
    assert result["summary"]["passed"] is False
    assert any("changed-line" in failure for failure in result["summary"]["failures"])


def test_a_diff_without_measurable_lines_is_not_applicable(
    gates: ModuleType, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    report = write_coverage(tmp_path, totals(95, 95))
    config = write_config(tmp_path)
    monkeypatch.setattr(gates, "git_base_revision", lambda root: "d" * 40)
    monkeypatch.setattr(gates, "run_diff_cover", lambda *args, **kwargs: diff_report(0, None))

    result = gates.run_thresholds(report, gates.load_policy(config), tmp_path)

    assert result["changed_lines"]["status"] == "not_applicable"
    assert result["summary"]["passed"] is True


def test_a_missing_diff_cover_report_fails_the_check(
    gates: ModuleType, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    report = write_coverage(tmp_path, totals(95, 95))
    config = write_config(tmp_path)
    monkeypatch.setattr(gates, "git_base_revision", lambda root: "e" * 40)
    monkeypatch.setattr(gates, "run_diff_cover", lambda *args, **kwargs: None)

    result = gates.run_thresholds(report, gates.load_policy(config), tmp_path)

    assert result["summary"]["passed"] is False
    assert any("diff-cover" in failure for failure in result["summary"]["failures"])


def test_diff_cover_compares_the_coverage_xml_with_the_baseline(
    gates: ModuleType, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """真实调用路径：命令行参数必须指向 coverage.xml 与基线 revision。"""
    captured: dict = {}

    def fake_run(command: list[str], **kwargs: object) -> object:
        captured["command"] = command
        report = Path(command[command.index("--json-report") + 1])
        report.write_text(json.dumps(diff_report(5, 80.0)), encoding="utf-8")

        class Done:
            returncode = 0

        return Done()

    monkeypatch.setattr(gates.subprocess, "run", fake_run)
    xml = tmp_path / "coverage.xml"
    xml.write_text("<coverage/>", encoding="utf-8")

    result = gates.run_diff_cover(tmp_path, "f" * 40, xml)

    assert result == diff_report(5, 80.0)
    assert "--compare-branch" in captured["command"]
    assert "f" * 40 in captured["command"]
    assert str(xml) in captured["command"]


def test_a_baseline_equal_to_head_falls_back_to_the_previous_commit(
    gates: ModuleType, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """直推 main 时 origin/main 就是 HEAD；门槛必须仍测量最近一次改动。"""
    revisions = {"origin/main": "a" * 40, "HEAD": "a" * 40, "HEAD~1": "b" * 40}
    monkeypatch.setattr(gates, "_rev_parse", lambda root, revision: revisions.get(revision))

    assert gates.git_base_revision(tmp_path) == "b" * 40


def test_a_baseline_that_differs_from_head_is_used_directly(
    gates: ModuleType, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    revisions = {"origin/main": "a" * 40, "HEAD": "c" * 40}
    monkeypatch.setattr(gates, "_rev_parse", lambda root, revision: revisions.get(revision))

    assert gates.git_base_revision(tmp_path) == "a" * 40
