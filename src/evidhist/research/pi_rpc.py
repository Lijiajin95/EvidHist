"""PI 的 RPC 管道：启动零工具的 PI 子进程、按 JSONL 协议对话、取回文本与 token 用量。

单独成模块的原因：协议细节（stdin/stdout、agent_settled、超时、优雅停机）与
研究流程（检索、论断、评审）关注点不同；执行器与评审器都只依赖这里的 `ask_pi`。
"""

from __future__ import annotations

import asyncio
import json
import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import cast

from evidhist.research.executor import ExecutorError, RunLimitExceeded, RunLimits

SETTLED_EVENT = "agent_settled"
LAST_TEXT_COMMAND = "get_last_assistant_text"
JSON_START = re.compile(r"[{]")
PI_THINKING_DEFAULT = "minimal"


@dataclass(frozen=True)
class PiConfig:
    """PI 的启动配置：模型、隔离 HOME、会话目录与可选的可执行文件目录。"""

    provider: str
    model: str
    home: Path
    session_dir: Path
    workdir: Path
    command: str = "pi"
    bin_dir: Path | None = None
    thinking: str = PI_THINKING_DEFAULT


async def ask_pi(config: PiConfig, prompt: str, limits: RunLimits) -> tuple[str, dict[str, int]]:
    """跑一次 PI RPC 会话（零工具），返回最终助手文本与 token 用量。"""
    argv = [config.command, *_rpc_flags(config)]
    process = await asyncio.create_subprocess_exec(
        *argv,
        stdin=asyncio.subprocess.PIPE,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
        env=_env(config),
        cwd=str(config.workdir),
    )
    try:
        return await asyncio.wait_for(
            _converse(process, prompt, limits), timeout=limits.wall_seconds
        )
    except TimeoutError as error:
        raise RunLimitExceeded("timeout") from error
    finally:
        await _shutdown(process)


def _rpc_flags(config: PiConfig) -> list[str]:
    """PI 的启动参数：RPC 模式且关闭全部通用工具（M07）。"""
    return [
        "--mode",
        "rpc",
        "--no-session",
        "--provider",
        config.provider,
        "--model",
        config.model,
        "--thinking",
        config.thinking,
        "--no-tools",
        "--no-mcp",
        "--no-extensions",
        "--no-skills",
        "--no-context-files",
        "--session-dir",
        str(config.session_dir),
    ]


def _env(config: PiConfig) -> dict[str, str]:
    env = os.environ.copy()
    env["HOME"] = str(config.home)
    if config.bin_dir is not None:
        env["PATH"] = f"{config.bin_dir}:{env.get('PATH', '')}"
    return env


async def _converse(
    process: asyncio.subprocess.Process, prompt: str, limits: RunLimits
) -> tuple[str, dict[str, int]]:
    _send(process, {"id": "prompt-1", "type": "prompt", "message": prompt})
    usage = await _wait_settled(process, limits.idle_seconds)
    _send(process, {"id": "text-1", "type": LAST_TEXT_COMMAND})
    return await _wait_text(process, limits.idle_seconds), usage


def _send(process: asyncio.subprocess.Process, payload: dict[str, object]) -> None:
    # 进程由 create_subprocess_exec(stdin=PIPE, stdout=PIPE) 创建，管道必然存在。
    stdin = cast("asyncio.StreamWriter", process.stdin)
    stdin.write((json.dumps(payload, ensure_ascii=False) + "\n").encode("utf-8"))


async def _read_line(process: asyncio.subprocess.Process, timeout: float) -> bytes:
    stdout = cast("asyncio.StreamReader", process.stdout)
    try:
        return await asyncio.wait_for(stdout.readline(), timeout=timeout)
    except TimeoutError as error:
        raise RunLimitExceeded("timeout") from error


async def _wait_settled(process: asyncio.subprocess.Process, idle_seconds: float) -> dict[str, int]:
    usage = {"input": 0, "output": 0}
    while True:
        line = await _read_line(process, idle_seconds)
        if not line:
            raise ExecutorError("process_exited")
        record = _decode(line)
        if record is None:
            continue
        add_tokens(usage, _usage_of(record))
        if record.get("type") == SETTLED_EVENT:
            return usage


async def _wait_text(process: asyncio.subprocess.Process, idle_seconds: float) -> str:
    while True:
        line = await _read_line(process, idle_seconds)
        if not line:
            raise ExecutorError("process_exited")
        record = _decode(line)
        if record is None:
            continue
        if record.get("type") == "response" and record.get("command") == LAST_TEXT_COMMAND:
            data = record.get("data")
            return (
                str(cast("dict[str, object]", data).get("text", ""))
                if isinstance(data, dict)
                else ""
            )


def _decode(line: bytes) -> dict[str, object] | None:
    try:
        record = json.loads(line.decode("utf-8"))
    except json.JSONDecodeError:
        return None
    return cast("dict[str, object]", record) if isinstance(record, dict) else None


def _usage_of(record: dict[str, object]) -> dict[str, int]:
    message = record.get("message")
    if not isinstance(message, dict):
        return {}
    usage = cast("dict[str, object]", message).get("usage")
    if not isinstance(usage, dict):
        return {}
    entry = cast("dict[str, object]", usage)
    return {
        "input": as_int(entry.get("input")),
        "output": as_int(entry.get("output")),
    }


def as_int(value: object) -> int:
    return value if isinstance(value, int) else 0


def add_tokens(total: dict[str, int], extra: dict[str, int]) -> None:
    for key in ("input", "output"):
        total[key] = total.get(key, 0) + int(extra.get(key, 0) or 0)


async def _shutdown(process: asyncio.subprocess.Process) -> None:
    if process.stdin is not None and not process.stdin.is_closing():
        process.stdin.close()
    try:
        await asyncio.wait_for(process.wait(), timeout=10)
    except TimeoutError:  # pragma: no cover - 进程不退出时的兜底
        process.kill()
        await process.wait()


def extract_json(text: str) -> dict[str, object] | None:
    """从模型输出里取出第一个完整 JSON 对象；允许前后有解释文字。"""
    decoder = json.JSONDecoder()
    for match in JSON_START.finditer(text):
        try:
            data: object = decoder.raw_decode(text[match.start() :])[0]
        except json.JSONDecodeError:
            continue
        if isinstance(data, dict):
            return cast("dict[str, object]", data)
    return None
