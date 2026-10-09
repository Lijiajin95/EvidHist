import { describe, expect, it } from "vitest";
import {
  codePointLength,
  isEmptyRange,
  splitByCodePointRange,
  utf16IndexFromCodePoint,
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
