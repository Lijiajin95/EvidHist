"""PI 流式协议（`stream_pi`）的组件测试：真实增量、最终文本与超时。

用小假 PI 进程跑协议，不调用真实模型；增量顺序与最终文本一致性都从 stdout 观察。
"""

from __future__ import annotations

import stat
from pathlib import Path

import pytest

from evidhist.research.executor import RunLimitExceeded, RunLimits
from evidhist.research.pi_rpc import PiConfig, TextDelta, TurnResult, stream_pi

REPO = Path(__file__).resolve().parents[2]
FAKE_PI = REPO / "tests" / "fixtures" / "fake_pi.py"
LIMITS = RunLimits(wall_seconds=30, idle_seconds=5)


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


async def collect(tmp_path: Path, prompt: str) -> tuple[list[str], list[TurnResult]]:
    deltas: list[str] = []
    results: list[TurnResult] = []
    async for item in stream_pi(config(tmp_path), prompt, LIMITS):
        if isinstance(item, TextDelta):
            deltas.append(item.text)
        else:
            results.append(item)
    return deltas, results


async def test_deltas_arrive_in_order_and_join_into_the_final_text(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("FAKE_PI_MODE", "ok")

    deltas, results = await collect(tmp_path, "只回答两个字：于謙")

    assert len(deltas) > 1
    assert len(results) == 1
    assert "".join(deltas) == results[0].text
    assert results[0].usage["input"] == 120
    assert results[0].usage["output"] == 30


async def test_an_unsettled_process_times_out(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("FAKE_PI_MODE", "unsettled")

    with pytest.raises(RunLimitExceeded) as error:
        async for _item in stream_pi(config(tmp_path), "问题", LIMITS):
            pass

    assert error.value.reason == "timeout"
