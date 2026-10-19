import { describe, expect, it } from "vitest";

import { cleanAnswerText } from "../../src/components/chat/answerText";

/** 取自演示库里两条旧回答的原文片段（旧提示词要求写 version_id 与区间）。 */
const OLD_BULLETS = [
  "工具结果没有给出作品名与卷次，只能按 `version_id` 与字符区间标注：",
  "",
  "1. **景泰/土木之变语境中的“京師”指北京。**",
  "   - `version_id: 0013e595-...`，区间 `3607–3609`：“于謙請駐兵居庸，寇來則出關勦殺，退則就糧**京師**。”",
  "   - 同版本 `read` 区间 `3500–3700` 同段有“鹵分道入寇陽和、大同偏頭關、野狐嶺”等。",
  "   - 同版本区间 `6522–6524`：“設彼假送駕之名，來犯**京師**”。",
  "",
  "以上判断仅依据所给检索片段和 `version_id`、字符区间推得。",
].join("\n");

const OLD_TABLE = [
  "## 依据（作品／卷次／区间）",
  "",
  "| 作品 | 卷次 | 区间（字符） | 要点 |",
  "|---|---|---|---|",
  "| 明史 | 卷167 | 4088–4092 | 「土木之變，也先擁帝北去」 |",
  "| 明通鑑 | 卷029 | 5664–5668 | 「初土木之變，楊俊自獨石奔還」 |",
  "",
  "（作品／卷次对应关系取自 `list_materials`：`0013e595-…` = 明通鑑 卷029；`049f393d-…` = 明史 卷172。）",
  "",
  "补充说明：明通鑑卷029 区间 7032–7034 的「土木繁興」与战事无关。",
].join("\n");

describe("cleanAnswerText", () => {
  it("hides version ids and code point ranges but keeps the quotes", () => {
    const { text, hidden } = cleanAnswerText(OLD_BULLETS);

    expect(text).not.toContain("version_id");
    expect(text).not.toContain("0013e595");
    expect(text).not.toContain("3607");
    expect(text).not.toContain("3500");
    expect(text).not.toContain("6522");
    expect(text).toContain("于謙請駐兵居庸，寇來則出關勦殺，退則就糧**京師**。");
    expect(text).toContain("同版本");
    expect(hidden).toBeGreaterThan(0);
  });

  it("drops the range column, the id mapping note and the range wording", () => {
    const { text } = cleanAnswerText(OLD_TABLE);

    expect(text).toContain("## 依据（材料·卷次）");
    expect(text).not.toContain("区间");
    expect(text).not.toContain("4088");
    expect(text).not.toContain("5664");
    expect(text).not.toContain("7032");
    expect(text).not.toContain("0013e595");
    expect(text).toContain("| 明史 | 卷167 | 「土木之變，也先擁帝北去」 |");
    expect(text).toContain("补充说明：明通鑑卷029 的「土木繁興」与战事无关。");
  });

  it("leaves ordinary prose untouched", () => {
    const prose = "于謙在 1449 年主持北京防務，見《明史》卷170。";

    expect(cleanAnswerText(prose)).toEqual({ text: prose, hidden: 0 });
  });

  it("hides closed range notation and returns a count", () => {
    const { text, hidden } = cleanAnswerText("引用区间 [3607, 3610) 的原文。");

    expect(text).toBe("引用 的原文。");
    expect(hidden).toBe(1);
  });
});
