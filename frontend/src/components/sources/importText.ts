export type ImportOutcome =
  { kind: "ignored" } | { kind: "loaded"; text: string } | { kind: "error"; message: string };

/**
 * Read the .txt the user selected. A replacement character means the bytes were
 * not UTF-8, so the text is reported as an error instead of becoming material.
 * Read failures propagate; the caller decides how to report them.
 */
export async function readUtf8Text(file: File | undefined): Promise<ImportOutcome> {
  if (file === undefined) {
    return { kind: "ignored" };
  }
  const text = await file.text();
  if (text.includes("\uFFFD")) {
    return { kind: "error", message: "文件不是有效的 UTF-8 文本，请转换编码后重试。" };
  }
  return { kind: "loaded", text };
}
