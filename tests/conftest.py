"""Shared test configuration; external services are enabled only by explicit test targets."""

import os
import tomllib
from pathlib import Path

import pytest
from hypothesis import settings
from sqlalchemy.engine import make_url

ROOT = Path(__file__).resolve().parents[1]


def _register_property_profiles() -> None:
    """Register the local/ci/extended Hypothesis budgets from the quality policy."""
    policy = tomllib.loads((ROOT / "config/quality-policy.toml").read_text(encoding="utf-8"))
    profiles = policy["property_tests"]
    settings.register_profile(
        "evidhist-local",
        max_examples=profiles["local_examples"],
        deadline=200,
        derandomize=False,
    )
    settings.register_profile(
        "evidhist-ci",
        max_examples=profiles["ci_examples"],
        deadline=None,
        derandomize=True,
    )
    settings.register_profile(
        "evidhist-extended",
        max_examples=profiles["extended_examples"],
        deadline=None,
        derandomize=False,
    )


_register_property_profiles()


@pytest.fixture(scope="session")
def database_url() -> str:
    value = os.environ.get("EVIDHIST_TEST_DATABASE_URL")
    if value is None:
        pytest.fail(
            "Set EVIDHIST_TEST_DATABASE_URL or use a database test target; tests are not skipped."
        )
    if make_url(value).database != "evidhist_test":
        pytest.fail("Database tests require the isolated evidhist_test database.")
    return value
