"""Tool-gate negative examples: every hard threshold must be discoverable.

Each case runs the real tool in a controlled temporary project so the boundary
behavior is a regression test: Ruff complexity 11 and six parameters fail while the
boundary values pass; Import Linter detects a forbidden architecture dependency;
pytest-timeout kills a stuck test under the signal method on this platform; deptry
fails a dev-group import unless the inline ignore documents the reason.
"""

import subprocess
import sys
from pathlib import Path

# Tools must be co-installed with the running interpreter: inside the mutants
# sandbox the test file lives under mutants/, but sys.executable still points at
# the repository virtualenv that owns ruff, deptry, lint-imports and pytest.
VENV = Path(sys.executable).parent


def run_tool(command: list[str], cwd: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(command, cwd=cwd, capture_output=True, text=True, check=False)


def write_nested_ifs(path: Path, count: int) -> None:
    lines = ["def evaluate(value):"]
    for level in range(count):
        lines.append(f"{'    ' * (level + 1)}if value > {level}:")
    lines.append(f"{'    ' * (count + 1)}return 10")
    lines.append("    return 0")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def test_complexity_eleven_is_rejected_and_ten_passes(tmp_path: Path) -> None:
    write_nested_ifs(tmp_path / "complex11.py", 10)
    write_nested_ifs(tmp_path / "complex10.py", 9)
    command = [str(VENV / "ruff"), "check", "--isolated", "--select", "C901"]

    rejected = run_tool([*command, "complex11.py"], tmp_path)
    accepted = run_tool([*command, "complex10.py"], tmp_path)

    assert rejected.returncode == 1
    assert "too complex (11 > 10)" in rejected.stdout
    assert accepted.returncode == 0


def test_six_parameters_are_rejected_and_five_pass(tmp_path: Path) -> None:
    (tmp_path / "params5.py").write_text(
        "def five(a, b, c, d, e):\n    return a + b + c + d + e\n", encoding="utf-8"
    )
    (tmp_path / "params6.py").write_text(
        "def six(a, b, c, d, e, f):\n    return a + b + c + d + e + f\n", encoding="utf-8"
    )
    command = [str(VENV / "ruff"), "check", "--isolated", "--select", "PLR0913"]

    rejected = run_tool([*command, "params6.py"], tmp_path)
    accepted = run_tool([*command, "params5.py"], tmp_path)

    assert rejected.returncode == 1
    assert "Too many arguments in function definition (6 > 5)" in rejected.stdout
    assert accepted.returncode == 0


def write_fake_project(tmp_path: Path, domain_source: str) -> None:
    domain = tmp_path / "fakeproj" / "domain"
    api = tmp_path / "fakeproj" / "api"
    domain.mkdir(parents=True)
    api.mkdir(parents=True)
    (tmp_path / "fakeproj" / "__init__.py").touch()
    (api / "__init__.py").touch()
    (domain / "__init__.py").write_text(domain_source, encoding="utf-8")
    (tmp_path / "pyproject.toml").write_text(
        '[tool.importlinter]\nroot_package = "fakeproj"\n\n'
        '[[tool.importlinter.contracts]]\nname = "test"\ntype = "forbidden"\n'
        'source_modules = ["fakeproj.domain"]\nforbidden_modules = ["fakeproj.api"]\n'
        "allow_indirect_imports = false\n",
        encoding="utf-8",
    )


def test_forbidden_architecture_dependency_breaks_the_contract(tmp_path: Path) -> None:
    write_fake_project(tmp_path, "import fakeproj.api\n")

    result = run_tool(
        [str(VENV / "lint-imports"), "--config", "pyproject.toml", "--no-cache"], tmp_path
    )

    assert result.returncode == 1
    assert "fakeproj.domain is not allowed to import fakeproj.api" in result.stdout


def test_clean_fake_package_keeps_the_contract(tmp_path: Path) -> None:
    write_fake_project(tmp_path, "VALUE = 1\n")

    result = run_tool(
        [str(VENV / "lint-imports"), "--config", "pyproject.toml", "--no-cache"], tmp_path
    )

    assert result.returncode == 0


def test_a_stuck_test_is_killed_by_the_timeout_gate(tmp_path: Path) -> None:
    (tmp_path / "sleepy_test.py").write_text(
        "import time\n\n\ndef test_sleepy():\n    time.sleep(5)\n", encoding="utf-8"
    )

    result = run_tool(
        [
            str(VENV / "pytest"),
            "sleepy_test.py",
            "--timeout=1",
            "--timeout-method=signal",
            "-p",
            "no:cacheprovider",
            "-q",
        ],
        tmp_path,
    )

    assert result.returncode == 1
    assert "Timeout (>1.0s)" in result.stdout


def write_deptry_project(tmp_path: Path, tooling_source: str) -> None:
    (tmp_path / "pyproject.toml").write_text(
        '[project]\nname = "deptry-negative"\nversion = "0.1.0"\n'
        'requires-python = ">=3.14"\ndependencies = []\n\n'
        '[dependency-groups]\ndev = ["pyyaml>=6,<7"]\n',
        encoding="utf-8",
    )
    (tmp_path / "tooling.py").write_text(tooling_source, encoding="utf-8")


def test_dev_dependency_import_without_a_documented_reason_fails(tmp_path: Path) -> None:
    write_deptry_project(tmp_path, "import yaml\n\n\ndef load():\n    return yaml.safe_load\n")

    result = run_tool([str(VENV / "deptry"), "."], tmp_path)

    assert result.returncode == 1
    assert "DEP004" in result.stderr


def test_dev_dependency_import_with_inline_ignore_passes(tmp_path: Path) -> None:
    write_deptry_project(
        tmp_path,
        "# dev tooling by design\nimport yaml  # deptry: ignore[DEP004]\n\n\ndef load():\n"
        "    return yaml.safe_load\n",
    )

    result = run_tool([str(VENV / "deptry"), "."], tmp_path)

    assert result.returncode == 0
