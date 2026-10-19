import json
from dataclasses import replace
from datetime import UTC, date, datetime, time
from pathlib import Path
from zoneinfo import ZoneInfo

import pytest

from evidhist.commit_policy import (
    CommitPolicy,
    WorkdayCalendar,
    check_commit_time,
    validate_commit_message,
)


@pytest.fixture
def policy() -> CommitPolicy:
    data = json.loads(Path("config/workday-calendars/2026.json").read_text())
    calendar = WorkdayCalendar(
        2026,
        frozenset(date.fromisoformat(day) for day in data["holidays"]),
        frozenset(date.fromisoformat(day) for day in data["extra_workdays"]),
    )
    return CommitPolicy(ZoneInfo("Asia/Shanghai"), time(9), time(18), {2026: calendar})


@pytest.mark.parametrize(
    "stamp,allowed,reason",
    [
        ("2026-10-09T08:59:59+08:00", True, "outside_work_hours"),
        ("2026-10-09T09:00:00+08:00", False, "workday_work_hours"),
        ("2026-10-09T17:59:59+08:00", False, "workday_work_hours"),
        ("2026-10-09T18:00:00+08:00", True, "outside_work_hours"),
        ("2026-10-10T12:00:00+08:00", False, "workday_work_hours"),
        ("2026-10-11T12:00:00+08:00", True, "non_workday"),
        ("2026-10-01T12:00:00+08:00", True, "non_workday"),
        ("2026-01-04T12:00:00+08:00", False, "workday_work_hours"),
        ("2026-02-14T12:00:00+08:00", False, "workday_work_hours"),
        ("2026-10-09T01:00:00+00:00", False, "workday_work_hours"),
        ("2027-01-09T12:00:00+08:00", False, "calendar_missing"),
        ("2027-01-09T21:00:00+08:00", True, "outside_work_hours"),
    ],
)
def test_commit_rule_obeys_holidays_makeup_days_and_beijing_time(
    policy: CommitPolicy, stamp: str, allowed: bool, reason: str
) -> None:
    decision = check_commit_time(datetime.fromisoformat(stamp), policy)

    assert decision.allowed is allowed
    assert decision.reason == reason


def test_naive_timestamp_cannot_silently_use_machine_timezone(policy: CommitPolicy) -> None:
    with pytest.raises(ValueError, match="timezone"):
        check_commit_time(datetime(2026, 10, 9, 12), policy)


def test_allowed_commit_in_an_unmaintained_year_still_prompts_calendar_maintenance(
    policy: CommitPolicy,
) -> None:
    decision = check_commit_time(datetime.fromisoformat("2027-01-09T21:00:00+08:00"), policy)

    assert decision.allowed
    assert decision.reason == "outside_work_hours"
    assert decision.hint == "maintain_annual_calendar"


def test_maintained_years_do_not_attach_a_calendar_hint(policy: CommitPolicy) -> None:
    decision = check_commit_time(datetime.fromisoformat("2026-10-11T12:00:00+08:00"), policy)

    assert decision.allowed
    assert decision.hint is None


def test_bad_or_wrong_year_calendars_are_rejected() -> None:
    day = date(2026, 10, 10)
    with pytest.raises(ValueError, match="both"):
        WorkdayCalendar(2026, frozenset({day}), frozenset({day}))
    with pytest.raises(ValueError, match="declared year"):
        WorkdayCalendar(2025, frozenset({day}), frozenset())
    with pytest.raises(ValueError, match="cover"):
        WorkdayCalendar(2026, frozenset(), frozenset()).is_workday(date(2027, 1, 1))


def test_empty_or_overnight_restrictions_are_not_accepted_as_this_policy() -> None:
    with pytest.raises(ValueError, match="nonempty"):
        CommitPolicy(ZoneInfo("Asia/Shanghai"), time(18), time(9), {})


@pytest.mark.parametrize(
    "message",
    [
        "feat(api): 增加引用定位",
        "fix!: change contract",
        "docs: update guide\n\nExplain why.",
        "ci(frontend): add checks",
    ],
)
def test_conventional_headers_accept_chinese_descriptions_and_breaking_changes(
    message: str,
) -> None:
    validate_commit_message(message)


@pytest.mark.parametrize(
    "message",
    [
        "",
        "update stuff",
        "feature: add",
        "feat(): add",
        "feat: ",
        "feat:  add",
        "feat: add ",
        "fix: " + "a" * 101,
    ],
)
def test_invalid_commit_headers_are_rejected(message: str) -> None:
    with pytest.raises(ValueError):
        validate_commit_message(message)


def test_offset_crossing_midnight_is_classified_on_the_beijing_date(policy: CommitPolicy) -> None:
    decision = check_commit_time(datetime(2026, 10, 9, 16, tzinfo=UTC), policy)

    assert decision.allowed
    assert decision.reason == "outside_work_hours"


def test_disabling_enforcement_allows_commits_inside_workday_hours(
    policy: CommitPolicy,
) -> None:
    """本机不再受工作时段限制：开关关闭后，调休工作日午间也允许提交。"""
    relaxed = replace(policy, enforce_blocked_window=False)

    decision = check_commit_time(datetime.fromisoformat("2026-10-10T12:00:00+08:00"), relaxed)

    assert decision.allowed is True
    assert decision.reason == "blocked_window_disabled"


def test_disabled_enforcement_still_reminds_about_missing_calendars(
    policy: CommitPolicy,
) -> None:
    relaxed = replace(policy, enforce_blocked_window=False)

    decision = check_commit_time(datetime.fromisoformat("2027-03-01T12:00:00+08:00"), relaxed)

    assert decision.allowed is True
    assert decision.hint == "maintain_annual_calendar"


def test_enforcement_remains_the_default(policy: CommitPolicy) -> None:
    assert policy.enforce_blocked_window is True
