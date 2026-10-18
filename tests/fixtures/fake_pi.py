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


def _chat_reply(message: str) -> str | None:
    """对话循环的三种提示词：决定动作、Markdown 回答、论断与引文。"""
    if "请输出本轮论断与逐字引文" in message:
        citations = [
            item
            for item in _extract_objects(message)
            if {"version_id", "start", "end"} <= set(item)
            and ("exact_quote" in item or "quote" in item)
        ]
        if not citations:
            return json.dumps({"claims": []}, ensure_ascii=False)
        citation = citations[-1]
        exact_quote = citation.get("exact_quote") or citation["quote"]
        claim = {
            "statement": "于謙主張固守京師。",
            "citations": [
                {
                    "version_id": citation["version_id"],
                    "start": citation["start"],
                    "end": citation["end"],
                    "exact_quote": exact_quote,
                }
            ],
        }
        return json.dumps({"claims": [claim]}, ensure_ascii=False)
    if "请用 Markdown 回答" in message:
        return "## 结论\n\n于謙主張固守京師，见《明史》卷170。"
    if "请只输出下一步动作" in message:
        if "FORCE_TOOL" in message or "（无）" in message:
            action = {"action": "tool", "tool": "search", "arguments": {"query": "于謙"}}
        else:
            action = {"action": "final"}
        return json.dumps(action, ensure_ascii=False)
    return None


def _reply(mode: str, message: str) -> str:
    if mode == "garbage":
        return "我不会输出 JSON。"
    chat = _chat_reply(message)
    if chat is not None:
        return chat
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


def _chunks(text: str, size: int = 8) -> list[str]:
    return [text[index : index + size] for index in range(0, len(text), size)] or [""]


def _delta_records(text: str) -> list[dict]:
    """按 PI 的真实事件形状逐块输出正文增量（text_delta）。"""
    return [
        {
            "type": "message_update",
            "usage": {"input": 0, "output": 0},
            "assistantMessageEvent": {"type": "text_delta", "contentIndex": 0, "delta": chunk},
        }
        for chunk in _chunks(text)
    ]


def _prompt_records(request_id: object, mode: str, text: str = "") -> list[dict]:
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
        *_delta_records(text),
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
            _emit(_prompt_records(record.get("id"), mode, text))
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
