#!/usr/bin/env python3
"""测试替身：讲 PI RPC 协议的假 PI 进程（不含任何工具）。

行为由环境变量 FAKE_PI_MODE 控制：
- ok（默认）：按提示词返回结构化 JSON——检索计划 / 论断与引文 / 反证结论。
  论断引文直接取自提示词中的片段 JSON，因此与真实材料逐字一致。
- unsettled：输出 agent_end 但不输出 agent_settled，并保持进程存活（触发空闲超时）。
- garbage：最终文本不是 JSON（触发协议错误路径）。
"""

from __future__ import annotations

import json
import os
import sys
import time

SETTLED = "agent_settled"


def _extract_objects(text: str) -> list[dict]:
    decoder = json.JSONDecoder()
    found: list[dict] = []
    index = 0
    while index < len(text):
        start = text.find("{", index)
        if start == -1:
            break
        try:
            data = decoder.raw_decode(text[start:])[0]
        except json.JSONDecodeError:
            index = start + 1
            continue
        if isinstance(data, dict):
            found.append(data)
        index = start + 1
    return found


def _payload_with(message: str, key: str) -> dict | None:
    for candidate in reversed(_extract_objects(message)):
        if key in candidate:
            return candidate
    return None


def _reply(mode: str, message: str) -> str:
    if mode == "garbage":
        return "我不会输出 JSON。"
    if "verdict" in message:
        review = {
            "verdict": "pass",
            "checked_scope": "报告全文与引文位置",
            "comments": [{"target": "§2", "severity": "info", "comment": "引文与论断一致。"}],
        }
        return json.dumps(review, ensure_ascii=False)
    if "counter_queries" in message:
        return json.dumps({"queries": ["于謙"], "counter_queries": ["也先"]}, ensure_ascii=False)
    if "findings" in message:
        passages = (_payload_with(message, "passages") or {}).get("passages") or []
        finding = (
            f"反证检索命中 {len(passages)} 段，未见相反记载"
            if passages
            else "未找到反证（不等于不存在）"
        )
        return json.dumps({"findings": [finding]}, ensure_ascii=False)
    passages_payload = _payload_with(message, "passages")
    if passages_payload is not None:
        passages = passages_payload.get("passages") or []
        if not passages:
            return json.dumps({"claims": []}, ensure_ascii=False)
        passage = passages[0]
        quote = str(passage.get("text") or "")[:2]
        claim = {
            "statement": "据所引原文，于謙主张固守京師。",
            "citations": [
                {
                    "version_id": passage["version_id"],
                    "start": passage["start"],
                    "end": int(passage["start"]) + len(quote),
                    "exact_quote": quote,
                }
            ],
        }
        return json.dumps({"claims": [claim]}, ensure_ascii=False)
    return json.dumps({"queries": ["于謙"], "counter_queries": ["也先"]}, ensure_ascii=False)


def _emit(records: list[dict]) -> None:
    for record in records:
        sys.stdout.write(json.dumps(record, ensure_ascii=False) + "\n")
    sys.stdout.flush()


def _prompt_records(request_id: object, mode: str) -> list[dict]:
    records: list[dict] = [
        {
            "id": request_id,
            "type": "response",
            "command": "prompt",
            "success": True,
            "data": {"disposition": "started"},
        },
        {"type": "agent_start"},
        {"type": "turn_start"},
        {
            "type": "turn_end",
            "message": {
                "role": "assistant",
                "usage": {"input": 120, "output": 30, "totalTokens": 150},
            },
        },
        {"type": "agent_end"},
    ]
    if mode != "unsettled":
        records.append({"type": SETTLED})
    return records


def main() -> int:
    mode = os.environ.get("FAKE_PI_MODE", "ok")
    text = ""
    for raw in sys.stdin:
        line = raw.strip()
        if not line:
            continue
        try:
            record = json.loads(line)
        except json.JSONDecodeError:
            continue
        command = record.get("type")
        if command == "prompt":
            text = _reply(mode, str(record.get("message", "")))
            _emit(_prompt_records(record.get("id"), mode))
            if mode == "unsettled":
                time.sleep(30)
        elif command == "get_last_assistant_text":
            _emit(
                [
                    {
                        "id": record.get("id"),
                        "type": "response",
                        "command": "get_last_assistant_text",
                        "success": True,
                        "data": {"text": text},
                    }
                ]
            )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
