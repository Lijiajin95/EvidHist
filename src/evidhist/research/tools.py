"""只读资料工具：研究执行器访问已入库材料的唯一入口（M03/M07）。

- **只读**：只能列出、检索、读取、取逐字引文；没有写入、文件、网络或 shell。
- **可回查**：返回 `version_id` 与字符区间（Unicode 码点，End 开区间），与引文硬校验同一口径。
- **纯本地**：材料在构造时一次载入，工具自身不碰数据库、文件系统或网络。
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from hashlib import sha256

CONTEXT_CHARS = 20
DEFAULT_LIMIT = 20


class ToolError(ValueError):
    """稳定的失败原因码，同时作为属性与异常消息。"""

    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(code)


@dataclass(frozen=True)
class Material:
    """一份可用于检索与引用的入库材料（原文逐字保存）。"""

    version_id: str
    work: str
    volume: str
    text: str


class ReadOnlyTools:
    """四个只读工具；不提供任何写入或执行能力。"""

    def __init__(self, materials: Sequence[Material]) -> None:
        ordered = sorted(materials, key=lambda material: material.version_id)
        self._materials = {material.version_id: material for material in ordered}
        self._order = [material.version_id for material in ordered]

    def list_materials(self) -> list[dict[str, object]]:
        return [
            {
                "version_id": version_id,
                "work": self._materials[version_id].work,
                "volume": self._materials[version_id].volume,
                "chars": len(self._materials[version_id].text),
            }
            for version_id in self._order
        ]

    def search(
        self,
        query: str,
        version_ids: Sequence[str] | None = None,
        limit: int = DEFAULT_LIMIT,
    ) -> list[dict[str, object]]:
        """纯子串检索（不排序打分、不做模糊匹配），返回全部命中位置与上下文。"""
        if not query.strip():
            raise ToolError("empty_query")
        if limit <= 0:
            raise ToolError("invalid_limit")
        hits: list[dict[str, object]] = []
        for version_id in self._targets(version_ids):
            text = self._materials[version_id].text
            start = text.find(query)
            while start != -1:
                end = start + len(query)
                hits.append(
                    {
                        "version_id": version_id,
                        "start": start,
                        "end": end,
                        "quote": query,
                        "context": text[
                            max(0, start - CONTEXT_CHARS) : min(len(text), end + CONTEXT_CHARS)
                        ],
                    }
                )
                if len(hits) >= limit:
                    return hits
                start = text.find(query, start + 1)
        return hits

    def read(self, version_id: str, start: int, end: int) -> dict[str, object]:
        """返回区间原文与该版本全文散列，供程序复核引用。"""
        material, quote = self._slice(version_id, start, end)
        return {
            "version_id": material.version_id,
            "start": start,
            "end": end,
            "text": quote,
            "version_sha256": sha256(material.text.encode("utf-8")).hexdigest(),
        }

    def exact_quote(self, version_id: str, start: int, end: int) -> str:
        """返回逐字原文，供执行器直接复制进论断，避免改写引文。"""
        return self._slice(version_id, start, end)[1]

    def _targets(self, version_ids: Sequence[str] | None) -> list[str]:
        if version_ids is None:
            return list(self._order)
        selected = set(version_ids)
        unknown = selected - set(self._materials)
        if unknown:
            raise ToolError("unknown_version")
        return [version_id for version_id in self._order if version_id in selected]

    def _slice(self, version_id: str, start: int, end: int) -> tuple[Material, str]:
        material = self._materials.get(version_id)
        if material is None:
            raise ToolError("unknown_version")
        if not 0 <= start < end <= len(material.text):
            raise ToolError("invalid_range")
        return material, material.text[start:end]
