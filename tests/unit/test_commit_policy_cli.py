"""Acceptance for the commit-policy CLI adapter: exit codes, audited revisions, injected time.

The script is a thin execution entry point around :mod:`evidhist.commit_policy`; these tests
inject explicit timestamps and controlled ``git`` output instead of creating real commits, so
they stay deterministic regardless of when the suite runs.
"""

import importlib.util
import subprocess
import sys
from collections.abc import Sequence
from datetime import datetime
from pathlib import Path
from types import ModuleType
from typing import Any

import pytest
from pytest import CaptureFixture, MonkeyPatch

SCRIPT_PATH = Path(__file__).resolve().parents[2] / "scripts" / "check_commit_policy.py"
HEAD_SHA = "a" * 40
BASE_SHA = "b" * 40
COMPLIANT_STAMP = "2026-10-11T12:00:00+08:00"  # Sunday noon in Beijing: allowed.
BLOCKED_STAMP = "2026-10-09T12:00:00+08:00"  # Statutory-workday Friday noon: rejected.
BLOCKED_STAMP_UTC = "2026-10-09T04:00:00+00:00"  # Same blocked instant expressed in UTC.


def load_cli_module() -> ModuleType:
    spec = importlib.util.spec_from_file_location("check_commit_policy_cli", SCRIPT_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class FrozenDatetime(datetime):
    """Real parsing and arithmetic, but ``now()`` answers with an injected instant."""

    frozen_now = datetime.fromisoformat("2026-10-09T12:00:00+08:00")

    @classmethod
    def now(cls, tz: Any = None) -> FrozenDatetime:
        stamp = cls.frozen_now if tz is None else cls.frozen_now.astimezone(tz)
        return cls.fromisoformat(stamp.isoformat())


class FakeCompleted:
    def __init__(self, stdout: str) -> None:
        self.stdout = stdout


class FakeGit:
    """Stands in for the script's ``subprocess`` reference; records requested commands."""

    CalledProcessError = subprocess.CalledProcessError

    def __init__(self, revisions: dict[str, str], log_lines: Sequence[str]) -> None:
        self.revisions = revisions
        self.log_lines = list(log_lines)
        self.log_targets: list[str] = []

    def run(self, arguments: list[str], **_kwargs: Any) -> FakeCompleted:
        if arguments[:2] == ["git", "rev-parse"]:
            requested = arguments[-1].removesuffix("^{commit}")
            if requested not in self.revisions:
                raise subprocess.CalledProcessError(128, arguments, "", "unknown revision")
            return FakeCompleted(self.revisions[requested] + "\n")
        if arguments[:2] == ["git", "log"]:
            self.log_targets.append(arguments[-1])
            return FakeCompleted("\n".join(self.log_lines))
        raise AssertionError(f"unexpected command {arguments}")


def log_line(subject: str, author: str = COMPLIANT_STAMP, committer: str | None = None) -> str:
    return "\0".join([HEAD_SHA, author, committer if committer else author, subject])


def run_cli(monkeypatch: MonkeyPatch, cli: ModuleType, argv: Sequence[str]) -> int:
    monkeypatch.setattr(sys, "argv", ["check_commit_policy", *argv])
    return int(cli.main())


@pytest.fixture
def cli(monkeypatch: MonkeyPatch) -> ModuleType:
    module = load_cli_module()
    FrozenDatetime.frozen_now = datetime.fromisoformat("2026-10-09T12:00:00+08:00")
    monkeypatch.setattr(module, "datetime", FrozenDatetime)
    return module


def test_check_now_rejects_injected_workday_noon_and_allows_evening(
    monkeypatch: MonkeyPatch, cli: ModuleType, capsys: CaptureFixture[str]
) -> None:
    FrozenDatetime.frozen_now = datetime.fromisoformat(BLOCKED_STAMP)
    assert run_cli(monkeypatch, cli, ["--check-now"]) == 1
    assert "Commit blocked" in capsys.readouterr().err

    FrozenDatetime.frozen_now = datetime.fromisoformat("2026-10-09T19:00:00+08:00")
    assert run_cli(monkeypatch, cli, ["--check-now"]) == 0
    assert capsys.readouterr().err == ""


def test_check_now_in_an_unmaintained_year_allows_but_prompts_calendar_maintenance(
    monkeypatch: MonkeyPatch, cli: ModuleType, capsys: CaptureFixture[str]
) -> None:
    FrozenDatetime.frozen_now = datetime.fromisoformat("2027-01-09T21:00:00+08:00")

    assert run_cli(monkeypatch, cli, ["--check-now"]) == 0
    assert "calendar" in capsys.readouterr().err


def test_message_entry_point_maps_header_verdicts_to_exit_codes(
    monkeypatch: MonkeyPatch, cli: ModuleType, tmp_path: Path
) -> None:
    good = tmp_path / "good.txt"
    good.write_text("feat(api): 增加引用定位\n", encoding="utf-8")
    bad = tmp_path / "bad.txt"
    bad.write_text("feature: add\n", encoding="utf-8")

    assert run_cli(monkeypatch, cli, ["--message", str(good)]) == 0
    assert run_cli(monkeypatch, cli, ["--message", str(bad)]) == 1
    assert run_cli(monkeypatch, cli, ["--message", str(tmp_path / "missing.txt")]) == 1


def install_git(
    monkeypatch: MonkeyPatch, cli: ModuleType, revisions: dict[str, str], lines: Sequence[str]
) -> FakeGit:
    fake = FakeGit(revisions, lines)
    monkeypatch.setattr(cli, "subprocess", fake)
    return fake


def test_audit_of_compliant_commits_passes_even_when_run_inside_the_blocked_window(
    monkeypatch: MonkeyPatch, cli: ModuleType
) -> None:
    # The injected clock sits inside the blocked window; CI run time must not decide the audit.
    FrozenDatetime.frozen_now = datetime.fromisoformat(BLOCKED_STAMP)
    install_git(monkeypatch, cli, {"HEAD": HEAD_SHA, BASE_SHA: BASE_SHA}, [log_line("fix: ok")])

    assert run_cli(monkeypatch, cli, ["--audit", BASE_SHA, "HEAD"]) == 0


@pytest.mark.parametrize(
    "base",
    ["", "0" * 40],
    ids=["empty-base", "zero-base"],
)
def test_first_push_without_usable_base_audits_full_head_history(
    monkeypatch: MonkeyPatch, cli: ModuleType, base: str
) -> None:
    fake = install_git(monkeypatch, cli, {"HEAD": HEAD_SHA}, [log_line("feat: initial")])

    assert run_cli(monkeypatch, cli, ["--audit", base, "HEAD"]) == 0
    assert fake.log_targets == [HEAD_SHA]


def test_push_audit_restricts_to_the_new_revision_range(
    monkeypatch: MonkeyPatch, cli: ModuleType
) -> None:
    fake = install_git(monkeypatch, cli, {"HEAD": HEAD_SHA, BASE_SHA: BASE_SHA}, [])

    assert run_cli(monkeypatch, cli, ["--audit", BASE_SHA, "HEAD"]) == 0
    assert fake.log_targets == [f"{BASE_SHA}..{HEAD_SHA}"]


@pytest.mark.parametrize(
    "author,committer",
    [
        (BLOCKED_STAMP, COMPLIANT_STAMP),
        (COMPLIANT_STAMP, BLOCKED_STAMP),
        (BLOCKED_STAMP_UTC, COMPLIANT_STAMP),
    ],
    ids=["blocked-author", "blocked-committer", "blocked-author-utc"],
)
def test_audit_rejects_a_new_commit_when_either_timestamp_is_blocked(
    monkeypatch: MonkeyPatch,
    cli: ModuleType,
    capsys: CaptureFixture[str],
    author: str,
    committer: str,
) -> None:
    install_git(
        monkeypatch,
        cli,
        {"HEAD": HEAD_SHA, BASE_SHA: BASE_SHA},
        [log_line("feat: x", author, committer)],
    )

    assert run_cli(monkeypatch, cli, ["--audit", BASE_SHA, "HEAD"]) == 1
    assert f"Rejected commit {HEAD_SHA[:12]}" in capsys.readouterr().err


def test_audit_rejects_new_commits_with_invalid_headers(
    monkeypatch: MonkeyPatch, cli: ModuleType, capsys: CaptureFixture[str]
) -> None:
    install_git(
        monkeypatch, cli, {"HEAD": HEAD_SHA, BASE_SHA: BASE_SHA}, [log_line("update stuff")]
    )

    assert run_cli(monkeypatch, cli, ["--audit", BASE_SHA, "HEAD"]) == 1
    assert "Rejected commit" in capsys.readouterr().err


def test_unresolvable_or_invalid_revisions_fail_instead_of_passing(
    monkeypatch: MonkeyPatch, cli: ModuleType
) -> None:
    install_git(monkeypatch, cli, {}, [])
    assert run_cli(monkeypatch, cli, ["--audit", "0" * 40, "missing-ref"]) == 1

    install_git(monkeypatch, cli, {"HEAD": "not-a-sha", "0" * 40: HEAD_SHA}, [])
    assert run_cli(monkeypatch, cli, ["--audit", "0" * 40, "HEAD"]) == 1


def test_git_failures_surface_as_failed_checks(
    monkeypatch: MonkeyPatch, cli: ModuleType, capsys: CaptureFixture[str]
) -> None:
    def explode(arguments: list[str], **_kwargs: Any) -> None:
        raise subprocess.CalledProcessError(1, arguments)

    fake = install_git(monkeypatch, cli, {"HEAD": HEAD_SHA, BASE_SHA: BASE_SHA}, [])
    monkeypatch.setattr(fake, "run", explode)

    assert run_cli(monkeypatch, cli, ["--audit", BASE_SHA, "HEAD"]) == 1
    assert "failed" in capsys.readouterr().err


def test_validate_config_reports_maintained_years(
    monkeypatch: MonkeyPatch, cli: ModuleType, capsys: CaptureFixture[str]
) -> None:
    assert run_cli(monkeypatch, cli, ["--validate-config"]) == 0
    assert "2026" in capsys.readouterr().out
