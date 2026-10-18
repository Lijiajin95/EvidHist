"""Run the local SAST checks (bandit) over the project's Python sources.

bandit 属于 security 依赖组，配置在 pyproject.toml 的 [tool.bandit]；任何命中或工具
自身报错都返回非零，使 `make sast` 与 `make security` 失败。报告写入 reports/。
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

DEFAULT_TARGETS = ("src", "scripts")
DEFAULT_OUTPUT = Path("reports/bandit.json")
DEFAULT_CONFIG = Path("pyproject.toml")


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--target", action="append", default=[], help="扫描目录，可重复")
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT), help="JSON 报告路径")
    parser.add_argument("--config", default=str(DEFAULT_CONFIG), help="bandit 配置（TOML）")
    parser.add_argument("--bandit", default=".venv/bin/bandit", help="bandit 可执行文件")
    return parser.parse_args(argv)


def summarize(output: Path) -> None:
    """命中时给出报告位置，避免只在日志里留一个退出码。"""
    try:
        payload = json.loads(output.read_text(encoding="utf-8"))
    except OSError, json.JSONDecodeError:
        return
    results = payload.get("results", [])
    if results:
        print(f"bandit 命中 {len(results)} 处，详见 {output}", file=sys.stderr)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(sys.argv[1:] if argv is None else argv)
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    targets = args.target or list(DEFAULT_TARGETS)
    command = [
        str(Path(args.bandit).resolve()),
        "-c",
        args.config,
        "-r",
        *targets,
        "-f",
        "json",
        "-o",
        str(output),
        "-q",
    ]
    result = subprocess.run(command, check=False)
    if result.returncode != 0:
        summarize(output)
    return result.returncode


if __name__ == "__main__":
    sys.exit(main())
