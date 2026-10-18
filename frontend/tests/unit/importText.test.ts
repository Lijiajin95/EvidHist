import { describe, expect, it, vi } from "vitest";

import { readUtf8Text } from "../../src/components/sources/importText";

describe("readUtf8Text", () => {
  it("ignores the empty selection", async () => {
    await expect(readUtf8Text(undefined)).resolves.toEqual({ kind: "ignored" });
  });

  it("returns the text of a valid UTF-8 file", async () => {
    const file = new File(["帝曰：善。"], "quote.txt", { type: "text/plain" });
    await expect(readUtf8Text(file)).resolves.toEqual({ kind: "loaded", text: "帝曰：善。" });
  });

  it("rejects text that is not valid UTF-8", async () => {
    const file = new File(["帝曰\ufffd善。"], "broken.txt", { type: "text/plain" });
    await expect(readUtf8Text(file)).resolves.toEqual({
      kind: "error",
      message: "文件不是有效的 UTF-8 文本，请转换编码后重试。",
    });
  });

  it("propagates a read failure so the caller can report it", async () => {
    const file = new File(["x"], "unreadable.txt", { type: "text/plain" });
    vi.spyOn(file, "text").mockRejectedValue(new Error("boom"));
    await expect(readUtf8Text(file)).rejects.toThrow("boom");
  });
});
