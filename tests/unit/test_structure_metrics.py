"""Boundary acceptance for the structure-metric counter behind config/quality-policy.toml.

These cases fix the counting calibers from the handoff section 8.2: 50/51 effective
function lines, 20/21 public interfaces and 500/501 physical file lines must land on
the correct side of each threshold, and the excluded/included line categories
(docstrings, comments, strings, decorators, nested ranges) are pinned by samples.
"""

import importlib.util
from pathlib import Path
from types import ModuleType
from typing import Any

import pytest

SCRIPT_PATH = Path(__file__).resolve().parents[2] / "scripts" / "check_structure_metrics.py"


@pytest.fixture(scope="module")
def counter() -> ModuleType:
    spec = importlib.util.spec_from_file_location("check_structure_metrics", SCRIPT_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def make_function(body_lines: int) -> str:
    body = "\n".join(f"    value_{index} = {index}" for index in range(body_lines))
    return f"def sample():\n{body}\n"


def make_class(methods: int) -> str:
    body = "\n".join(f"    def method_{index}(self): ..." for index in range(methods))
    return f"class Sample:\n{body}\n"


def functions_of(counter: ModuleType, source: str) -> dict[str, Any]:
    metrics = counter.python_metrics(source, "sample.py")[0]
    return {metric.name: metric for metric in metrics}


def classes_of(counter: ModuleType, source: str) -> dict[str, Any]:
    metrics = counter.python_metrics(source, "sample.py")[1]
    return {metric.name: metric for metric in metrics}


@pytest.mark.parametrize(
    "body_lines,expected",
    [(49, 50), (50, 51)],
    ids=["boundary-50-passes", "boundary-51-exceeds"],
)
def test_function_effective_line_boundaries(
    counter: ModuleType, body_lines: int, expected: int
) -> None:
    assert functions_of(counter, make_function(body_lines))["sample"].effective_lines == expected


def test_multiline_signatures_count_but_decorators_do_not(counter: ModuleType) -> None:
    signature = "def sample(\n    first: int,\n    second: int,\n) -> None:\n    pass\n"
    decorated = "@decorator\n@module.decorator\ndef sample():\n    pass\n"

    assert functions_of(counter, signature)["sample"].effective_lines == 5
    assert functions_of(counter, decorated)["sample"].effective_lines == 2


def test_blank_comment_and_docstring_lines_are_excluded_but_code_with_comments_counts(
    counter: ModuleType,
) -> None:
    source = (
        "def sample():\n"
        '    """Docstring line 1\n'
        "    Docstring line 2\n"
        '    """\n'
        "\n"
        "    # comment-only line\n"
        "    value = 1  # trailing comment on a code line\n"
    )

    assert functions_of(counter, source)["sample"].effective_lines == 2


def test_hash_inside_multiline_strings_is_code_not_a_comment(counter: ModuleType) -> None:
    source = 'def sample():\n    text = """\n    # not a comment\n    SELECT 1\n    """\n'

    assert functions_of(counter, source)["sample"].effective_lines == 5


def test_nested_functions_are_separate_units_and_stay_in_the_outer_range(
    counter: ModuleType,
) -> None:
    source = (
        "def outer():\n"
        '    """Outer doc."""\n'
        "    def inner():\n"
        '        """Inner doc."""\n'
        "        pass\n"
        "    return inner\n"
    )
    metrics = functions_of(counter, source)

    assert metrics["outer"].effective_lines == 4
    assert metrics["inner"].effective_lines == 2
    assert metrics["inner"].kind == "function"


def test_lambdas_and_async_functions_are_counted_units(counter: ModuleType) -> None:
    source = "async def fetch():\n    await load()\n\n\ndef make():\n    add = lambda a, b: a + b\n    return add\n"
    metrics = functions_of(counter, source)

    assert metrics["fetch"].kind == "async_function"
    assert metrics["fetch"].effective_lines == 2
    assert metrics["<lambda>"].kind == "lambda"
    assert metrics["<lambda>"].effective_lines == 1


def test_python_314_era_syntax_parses_and_counts(counter: ModuleType) -> None:
    source = (
        "type Alias = int\n"
        "class Container[T]:\n"
        "    def unwrap(self, item: T) -> T:\n"
        "        match item:\n"
        "            case int() | float():\n"
        "                return item\n"
        "        return item\n"
    )
    metrics = classes_of(counter, source)

    assert functions_of(counter, source)["unwrap"].effective_lines == 5
    assert metrics["Container"].public_interfaces == 1


@pytest.mark.parametrize(
    "methods,expected",
    [(20, 20), (21, 21)],
    ids=["boundary-20", "boundary-21"],
)
def test_public_interface_boundaries(counter: ModuleType, methods: int, expected: int) -> None:
    assert classes_of(counter, make_class(methods))["Sample"].public_interfaces == expected


def test_property_accessors_and_overloads_merge_into_single_interfaces(
    counter: ModuleType,
) -> None:
    properties = (
        "class Sample:\n"
        "    @property\n"
        "    def size(self):\n"
        "        return 0\n"
        "\n"
        "    @size.setter\n"
        "    def size(self, value):\n"
        "        pass\n"
    )
    overloads = (
        "class Loader:\n"
        "    @overload\n"
        "    def load(self, value: int) -> int: ...\n"
        "    @overload\n"
        "    def load(self, value: str) -> str: ...\n"
        "    def load(self, value):\n"
        "        return value\n"
    )

    assert classes_of(counter, properties)["Sample"].public_interfaces == 1
    assert classes_of(counter, overloads)["Loader"].public_interfaces == 1


def test_static_and_instance_receivers_private_and_inherited_members_are_classified(
    counter: ModuleType,
) -> None:
    source = (
        "class Base:\n"
        "    def inherited(self): ...\n"
        "\n"
        "class Sample(Base):\n"
        "    @staticmethod\n"
        "    def build(): ...\n"
        "\n"
        "    def make(self): ...\n"
        "\n"
        "    def _private(self): ...\n"
        "\n"
        "    def __init__(self): ...\n"
        "\n"
        "    def __repr__(self): ...\n"
    )
    metrics = classes_of(counter, source)

    assert metrics["Sample"].public_interfaces == 2
    assert metrics["Sample"].interfaces == (("instance", "make"), ("static", "build"))
    assert metrics["Base"].public_interfaces == 1


def test_review_hints_count_own_scope_only(counter: ModuleType) -> None:
    source = (
        "def sample(first, second):\n"
        "    total = first\n"
        "    for index in range(3):\n"
        "        total = index\n"
        "    with open('x') as handle:\n"
        "        pass\n"
        "    try:\n"
        "        pass\n"
        "    except ValueError as error:\n"
        "        return total\n"
        "    return second\n"
        "\n"
        "    def helper():\n"
        "        inner = 1\n"
        "        return inner\n"
    )
    metric = functions_of(counter, source)["sample"]

    assert metric.return_statements == 2
    assert metric.local_variables == 5
    assert metric.statements == 10


def write_policy(tmp_path: Path, **overrides: Any) -> Path:
    values = {
        "function_effective_lines_warn": 40,
        "function_effective_lines_max": 50,
        "public_interfaces_warn": 10,
        "public_interfaces_max": 20,
        "file_physical_lines_warn": 300,
        "file_physical_lines_max": 500,
        "reviewed_file_exception_ceiling": 1000,
        **overrides,
    }
    body = "\n".join(f"{key} = {value}" for key, value in values.items())
    content = (
        "schema_version = 1\n"
        "[scope]\n"
        'handwritten_roots = ["src"]\n'
        'extensions = [".py"]\n'
        "generated_roots = []\n"
        f"[structure]\n{body}\n"
        "exclude_blank_lines = true\n"
        "exclude_comment_only_lines = true\n"
        "exclude_python_docstrings = true\n"
        "include_signature = true\n"
        "include_nested_function_ranges = true\n"
        "reviewed_exceptions = []\n"
    )
    path = tmp_path / "quality-policy.toml"
    path.write_text(content, encoding="utf-8")
    return path


def write_source(tmp_path: Path, source: str) -> Path:
    source_dir = tmp_path / "src"
    source_dir.mkdir(exist_ok=True)
    (source_dir / "sample.py").write_text(source, encoding="utf-8")
    return source_dir


def test_gate_fails_only_above_the_hard_thresholds(counter: ModuleType, tmp_path: Path) -> None:
    config = write_policy(tmp_path)
    cases = [
        (make_function(49), True, "effective lines"),
        (make_function(50), False, "effective lines"),
        (make_class(20), True, "public interfaces"),
        (make_class(21), False, "public interfaces"),
        ("value = 1\n" * 500 + "value = 2\n", False, "physical lines"),
    ]
    for source, expected_pass, phrase in cases:
        write_source(tmp_path, source)
        report = counter.run_check(tmp_path, config)
        assert report["summary"]["passed"] is expected_pass, (phrase, report["summary"])
        if not expected_pass:
            assert any(phrase in failure for failure in report["summary"]["failures"])


def test_warn_levels_do_not_fail_the_check(counter: ModuleType, tmp_path: Path) -> None:
    config = write_policy(tmp_path)
    write_source(tmp_path, make_function(45) + make_class(15) + "value = 1\n" * 350)

    report = counter.run_check(tmp_path, config)

    assert report["summary"]["passed"] is True
    assert len(report["summary"]["warnings"]) == 3
    assert report["python"]["files"][0]["level"] == "warn"


def test_reviewed_file_exceptions_are_capped_by_the_ceiling(
    counter: ModuleType, tmp_path: Path
) -> None:
    write_source(tmp_path, "value = 1\n" * 600)
    config = write_policy(tmp_path)
    content = config.read_text(encoding="utf-8").replace(
        "reviewed_exceptions = []",
        'reviewed_exceptions = [{path = "src/sample.py", rule = "file_physical_lines", '
        'reason = "generated-length table", owner = "maintainer", review = "2026-10-09", '
        'recheck = "2027-01-09"}]',
    )
    config.write_text(content, encoding="utf-8")
    capped = counter.run_check(tmp_path, config)
    assert capped["summary"]["passed"] is True
    assert capped["python"]["files"][0]["level"] == "excepted"

    write_source(tmp_path, "value = 1\n" * 1001)
    over_ceiling = counter.run_check(tmp_path, config)
    assert over_ceiling["summary"]["passed"] is False
    assert any("ceiling" in failure for failure in over_ceiling["summary"]["failures"])


def test_invalid_policy_configurations_fail_instead_of_passing(
    counter: ModuleType, tmp_path: Path
) -> None:
    bad_version = write_policy(tmp_path)
    bad_version.write_text(
        bad_version.read_text(encoding="utf-8").replace("schema_version = 1", "schema_version = 2"),
        encoding="utf-8",
    )
    assert counter.run_check(tmp_path, bad_version)["summary"]["passed"] is False

    incomplete = write_policy(tmp_path)
    incomplete.write_text(
        incomplete.read_text(encoding="utf-8").replace("function_effective_lines_max = 50\n", ""),
        encoding="utf-8",
    )
    report = counter.run_check(tmp_path, incomplete)
    assert any("function_effective_lines_max" in error for error in report["config_errors"])

    changed_caliber = write_policy(tmp_path)
    changed_caliber.write_text(
        changed_caliber.read_text(encoding="utf-8").replace(
            "exclude_blank_lines = true", "exclude_blank_lines = false"
        ),
        encoding="utf-8",
    )
    report = counter.run_check(tmp_path, changed_caliber)
    assert any("exclude_blank_lines" in error for error in report["config_errors"])

    bad_exception = write_policy(tmp_path)
    bad_exception.write_text(
        bad_exception.read_text(encoding="utf-8").replace(
            "reviewed_exceptions = []", 'reviewed_exceptions = [{path = "src/sample.py"}]'
        ),
        encoding="utf-8",
    )
    report = counter.run_check(tmp_path, bad_exception)
    assert any("missing keys" in error for error in report["config_errors"])
