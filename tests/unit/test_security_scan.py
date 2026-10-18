"""本地 SAST 门槛的行为：四类危险模式必须被扫描拦下，干净模块必须通过。

bandit 属于 security 依赖组；未安装该组时跳过（`make security` 会真实执行扫描）。
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

pytest.importorskip("bandit", reason="security 依赖组未安装")

RUNNER = Path(__file__).resolve().parents[2] / "scripts" / "run_bandit.py"

VIOLATIONS = {
    "B605": "import os\n\n\ndef run() -> None:\n    os.system('ls')\n",
    "B307": "def run(text: str) -> None:\n    eval(text)\n",
    "B301": "import pickle\n\n\ndef load(payload: bytes) -> object:\n    return pickle.loads(payload)\n",
    "B501": (
        "import requests\n\n\ndef fetch(url: str) -> object:\n"
        "    return requests.get(url, verify=False)\n"
    ),
}


def _scan(target: Path, output: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [
            sys.executable,
            str(RUNNER),
            "--target",
            str(target),
            "--output",
            str(output),
            "--config",
            str(Path(__file__).resolve().parents[2] / "pyproject.toml"),
        ],
        capture_output=True,
        text=True,
        check=False,
    )


@pytest.mark.parametrize(("test_id", "source"), sorted(VIOLATIONS.items()))
def test_dangerous_patterns_are_reported(tmp_path: Path, test_id: str, source: str) -> None:
    module = tmp_path / "planted.py"
    module.write_text(source, encoding="utf-8")
    report = tmp_path / "bandit.json"

    result = _scan(tmp_path, report)

    assert result.returncode == 1, result.stderr
    assert f'"test_id": "{test_id}"' in report.read_text(encoding="utf-8")


def test_clean_module_passes(tmp_path: Path) -> None:
    (tmp_path / "clean.py").write_text(
        "def add(a: int, b: int) -> int:\n    return a + b\n", encoding="utf-8"
    )
    report = tmp_path / "bandit.json"

    result = _scan(tmp_path, report)

    assert result.returncode == 0, result.stderr
    assert '"results": []' in report.read_text(encoding="utf-8")
