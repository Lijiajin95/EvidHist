/**
 * 旧回答的正文里写死了内部标识与码点区间（当时的提示词要求这么写）。
 * 这里在渲染前把这两类内部信息隐去，只保留可读的文字与引文；
 * 变动的处数返回给界面，用一行小字如实说明「已隐藏 N 处」。
 */

export interface CleanedAnswer {
  text: string;
  hidden: number;
}

const FULL_UUID = /[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}/gi;
const SHORT_UUID = /[0-9a-f]{8}-(?:\.{2,}|…)/gi;
const ID_MAP_PAREN = /（[^（）\n]*[0-9a-f]{8}-(?:\.{2,}|…)[^（）\n]*）/g;
const VERSION_ID = /`?version_id`?[:：]?[ \t]*/gi;
const RANGE_WITH_WORD =
  /(?:字符区间|码点区间|码点|区间|偏移|位置)[ \t]*`?[[(（]?[ \t]*\d+[ \t]*[–—\-~][ \t]*\d+[ \t]*[\])）]?`?[ \t]*[：:]?/g;
const RANGE_PAIR =
  /(?:字符区间|码点区间|码点|区间|偏移)[ \t]*`?[[(（][ \t]*\d+[ \t]*,[ \t]*\d+[ \t]*[\])）]`?/g;
const HEADING_LABEL = /（作品[／/·]卷次[／/·]区间）/g;

function countMatches(pattern: RegExp, text: string): number {
  return [...text.matchAll(new RegExp(pattern.source, pattern.flags))].length;
}

/** 去掉内部编号：整段 id 映射括号、完整与截断的 UUID。 */
function stripIds(text: string): CleanedAnswer {
  let hidden = countMatches(ID_MAP_PAREN, text);
  let result = text.replace(ID_MAP_PAREN, "");
  hidden += countMatches(FULL_UUID, result) + countMatches(SHORT_UUID, result);
  result = result.replace(FULL_UUID, "").replace(SHORT_UUID, "");
  hidden += countMatches(VERSION_ID, result);
  result = result.replace(VERSION_ID, "版本");
  return { text: result, hidden };
}

/** 去掉码点区间：带「区间/码点/偏移」字样的起止数字。 */
function stripRanges(text: string): CleanedAnswer {
  let hidden = countMatches(RANGE_PAIR, text);
  let result = text.replace(RANGE_PAIR, "");
  hidden += countMatches(RANGE_WITH_WORD, result);
  result = result.replace(RANGE_WITH_WORD, "");
  return { text: result, hidden };
}

function isTableStart(header: string, separator: string): boolean {
  return header.trim().startsWith("|") && /^[\s|:-]+$/.test(separator) && separator.includes("-");
}

function readTable(lines: string[], start: number): string[] {
  const rows = [lines[start] ?? "", lines[start + 1] ?? ""];
  let cursor = start + 2;
  while ((lines[cursor] ?? "").trim().startsWith("|")) {
    rows.push(lines[cursor] ?? "");
    cursor += 1;
  }
  return rows;
}

function withoutColumn(row: string, drop: number): string {
  return row
    .split("|")
    .filter((_cell, at) => at !== drop)
    .join("|");
}

/** 表头带「区间/码点」的整列移除。 */
function dropRangeColumns(text: string): CleanedAnswer {
  const lines = text.split("\n");
  const kept: string[] = [];
  let hidden = 0;
  let index = 0;
  while (index < lines.length) {
    const header = lines[index] ?? "";
    if (!isTableStart(header, lines[index + 1] ?? "")) {
      kept.push(header);
      index += 1;
      continue;
    }
    const rows = readTable(lines, index);
    index += rows.length;
    const drop = header.split("|").findIndex((cell) => /区间|码点/.test(cell));
    if (drop < 0) {
      kept.push(...rows);
      continue;
    }
    hidden += rows.length;
    kept.push(...rows.map((row) => withoutColumn(row, drop)));
  }
  return { text: kept.join("\n"), hidden };
}

/** 清理替换留下的空标记：只剩项目符号/冒号的行、重复冒号、空行压缩。 */
function tidy(text: string): string {
  return text
    .split("\n")
    .map((line) =>
      line
        .replace(/`{2}/g, "")
        .replace(/：{2,}/g, "：")
        .replace(/^(\s*(?:[-*]|\d+\.))\s*[：:，,]\s*$/u, "$1")
        .replace(/[ \t]{2,}/g, " ")
        .replace(/[ \t]+$/g, ""),
    )
    .filter((line, at, all) => line.trim() !== "" || (all[at - 1] ?? "").trim() !== "")
    .join("\n")
    .trim();
}

/** 隐去回答里的内部编号与码点区间；`hidden` 是实际改动的处数。 */
export function cleanAnswerText(text: string): CleanedAnswer {
  const labelled = text.replace(HEADING_LABEL, "（材料·卷次）");
  const ids = stripIds(labelled);
  const ranges = stripRanges(ids.text);
  const columns = dropRangeColumns(ranges.text);
  return {
    text: tidy(columns.text),
    hidden: ids.hidden + ranges.hidden + columns.hidden + (labelled === text ? 0 : 1),
  };
}
