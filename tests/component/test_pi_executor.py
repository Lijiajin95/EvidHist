"""PiExecutor 的组件测试：用假 PI 子进程跑完整闭环（离线，不调用真实模型）。

对应[最小技术方案](../docs/minimal-technical-plan-2026-10-18.md)§4.2/§6/§9：
PI 本体零工具、工具由适配器代理、超时与协议错误如实上报。
"""

from __future__ import annotations

import os
import stat
import sys
from pathlib import Path

import pytest

from evidhist.research.executor import RunLimits
from evidhist.research.graph import ResearchJob, run_research
from evidhist.research.pi_executor import PiExecutor
from evidhist.research.pi_rpc import PiConfig
from evidhist.research.tools import Material

REPO = Path(__file__).resolve().parents[2]
FAKE_PI = REPO / "tests" / "fixtures" / "fake_pi.py"
MATERIALS = (
    Material(
        version_id="v-170",
        work="明史",
        volume="卷170",
        text="于謙字廷益，錢塘人。也先入寇，謙力主守京師。",
    ),
)
QUESTION = "于謙在京城守禦中的主張是什麼?"


def config(tmp_path: Path) -> PiConfig:
    FAKE_PI.chmod(FAKE_PI.stat().st_mode | stat.S_IXUSR)
    return PiConfig(
        provider="fake-provider",
        model="fake-model",
        home=tmp_path / "home",
        session_dir=tmp_path / "sessions",
        workdir=tmp_path,
        command=str(FAKE_PI),
    )


async def test_pi_executor_runs_the_graph_with_host_side_tools(tmp_path: Path) -> None:
    (tmp_path / "home").mkdir()
    result = await run_research(
        executor=PiExecutor(config(tmp_path)),
        materials=MATERIALS,
        job=ResearchJob(
            question=QUESTION,
            run_id="run-pi",
            limits=RunLimits(wall_seconds=30, idle_seconds=10, tool_calls=20),
        ),
    )
    assert result.stopped_reason is None
    assert result.claims and all(claim.ok for claim in result.claims)
    assert result.claims[0].citations[0].citation.exact_quote == "于謙"
    assert result.usage["model"] == "fake-model"
    assert result.usage["calls"] == 3
    assert result.usage["input_tokens"] == 360  # 三次调用各 120
    assert result.tool_calls > 0
    assert result.counter_scope["queries"] == ["也先"]


async def test_unsettled_pi_hits_the_idle_timeout(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    (tmp_path / "home").mkdir()
    monkeypatch.setenv("FAKE_PI_MODE", "unsettled")
    result = await run_research(
        executor=PiExecutor(config(tmp_path)),
        materials=MATERIALS,
        job=ResearchJob(
            question=QUESTION,
            run_id="run-timeout",
            limits=RunLimits(wall_seconds=20, idle_seconds=1, tool_calls=20),
        ),
    )
    assert result.stopped_reason == "timeout"
    assert result.claims == ()


async def test_non_json_reply_is_reported_as_protocol_error(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    (tmp_path / "home").mkdir()
    monkeypatch.setenv("FAKE_PI_MODE", "garbage")
    result = await run_research(
        executor=PiExecutor(config(tmp_path)),
        materials=MATERIALS,
        job=ResearchJob(
            question=QUESTION,
            run_id="run-garbage",
            limits=RunLimits(wall_seconds=20, idle_seconds=5, tool_calls=20),
        ),
    )
    assert result.stopped_reason == "plan_not_json"
    assert result.claims == ()


def test_fixture_is_a_standalone_script() -> None:
    assert FAKE_PI.exists()
    assert sys.executable  # 解释器存在，夹具可执行
    assert os.access(FAKE_PI, os.R_OK)
