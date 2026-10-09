import { describe, expect, it } from "vitest";
import {
  codePointLength,
  isEmptyRange,
  splitByCodePointRange,
  utf16IndexFromCodePoint,
  utf16IndexToCodePoint,
} from "../../src/domain/offsets";

describe("code point ↔ UTF-16 offset mapping", () => {
  it("maps BMP characters one-to-one", () => {
    expect(utf16IndexFromCodePoint("甲乙丙", 2)).toBe(2);
    expect(codePointLength("甲乙丙")).toBe(3);
  });

  it("counts supplementary-plane characters as one code point and two UTF-16 units", () => {
    expect(codePointLength("甲𠀀乙")).toBe(3);
    expect(utf16IndexFromCodePoint("甲𠀀乙", 1)).toBe(1);
    expect(utf16IndexFromCodePoint("甲𠀀乙", 2)).toBe(3);
    expect(utf16IndexFromCodePoint("甲𠀀乙", 3)).toBe(4);
  });

  it("keeps surrogate halves intact when slicing a highlighted range", () => {
    expect(splitByCodePointRange("甲𠀀乙", 1, 2)).toEqual({
      before: "甲",
      quote: "𠀀",
      after: "乙",
    });
  });

  it("handles a range covering the whole astral string", () => {
    expect(splitByCodePointRange("𠀀𠀁𠀂", 0, 3)).toEqual({
      before: "",
      quote: "𠀀𠀁𠀂",
      after: "",
    });
  });

  it("treats combining marks as separate code points", () => {
    expect(splitByCodePointRange("a\u0301b", 1, 2)).toEqual({
      before: "a",
      quote: "\u0301",
      after: "b",
    });
  });

  it("flags empty ranges so the UI can show an empty result", () => {
    expect(isEmptyRange(3, 3)).toBe(true);
    expect(isEmptyRange(4, 3)).toBe(true);
    expect(isEmptyRange(0, 1)).toBe(false);
  });
});

describe("utf16 index to code point (selection boundaries)", () => {
  it("maps boundaries around an astral character", () => {
    expect(utf16IndexToCodePoint("甲𠀀乙", 0)).toBe(0);
    expect(utf16IndexToCodePoint("甲𠀀乙", 1)).toBe(1);
    expect(utf16IndexToCodePoint("甲𠀀乙", 3)).toBe(2);
    expect(utf16IndexToCodePoint("甲𠀀乙", 4)).toBe(3);
  });

  it("includes the whole surrogate pair when a boundary lands inside it", () => {
    // UTF-16 index 2 is the low surrogate of 𠀀: a selection ending there
    // still counts the visible character, so the end maps past the pair.
    expect(utf16IndexToCodePoint("甲𠀀乙", 2)).toBe(2);
    expect(splitByCodePointRange("甲𠀀乙", 0, 2).quote).toBe("甲𠀀");
  });

  it("maps combining marks and newline boundaries", () => {
    expect(utf16IndexToCodePoint("a\u0301b", 1)).toBe(1);
    expect(utf16IndexToCodePoint("a\u0301b", 2)).toBe(2);
    expect(utf16IndexToCodePoint("甲\n乙", 1)).toBe(1);
    expect(utf16IndexToCodePoint("甲\n乙", 2)).toBe(2);
  });
});
