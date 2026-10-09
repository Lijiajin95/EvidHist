import fc from "fast-check";
import { describe, it } from "vitest";
import {
  codePointLength,
  splitByCodePointRange,
  utf16IndexFromCodePoint,
  utf16IndexToCodePoint,
} from "../../src/domain/offsets";
import { propertyParameters } from "./propertyParameters";

/** UTF-16 strings with astral, BMP, combining and newline characters. */
const textArbitrary = fc
  .array(fc.constantFrom("甲", "乙", "𠀀", "𠀁", "a", "\u0301", "𠮷", "\n"), { minLength: 0 })
  .map((characters) => characters.join(""));

describe("offset mapping properties", () => {
  it("the utf16→code point mapping is the inverse at code point boundaries", () => {
    fc.assert(
      fc.property(textArbitrary, fc.nat(), (text, index) => {
        const bounded = Math.min(index, codePointLength(text));
        const utf16 = utf16IndexFromCodePoint(text, bounded);
        return utf16IndexToCodePoint(text, utf16) === bounded;
      }),
      propertyParameters,
    );
  });

  it("utf16→code point counts the code points before a boundary and clamps at the end", () => {
    fc.assert(
      fc.property(textArbitrary, fc.nat(), (text, index) => {
        const bounded = Math.min(index, text.length);
        const expected = Array.from(text.slice(0, bounded)).length;
        return utf16IndexToCodePoint(text, bounded) === expected;
      }),
      propertyParameters,
    );
  });

  it("joining the highlight segments reproduces the original text", () => {
    fc.assert(
      fc.property(textArbitrary, fc.nat(), fc.nat(), (text, start, end) => {
        const segments = splitByCodePointRange(text, Math.min(start, end), Math.max(start, end));
        return segments.before + segments.quote + segments.after === text;
      }),
      propertyParameters,
    );
  });

  it("the highlighted quote equals the code points inside the range", () => {
    fc.assert(
      fc.property(textArbitrary, fc.nat(), fc.nat(), (text, start, end) => {
        const from = Math.min(start, end);
        const to = Math.max(start, end);
        const expected = Array.from(text).slice(from, to).join("");
        return splitByCodePointRange(text, from, to).quote === expected;
      }),
      propertyParameters,
    );
  });

  it("utf16 indices point at code-point boundaries and match Array.from", () => {
    fc.assert(
      fc.property(textArbitrary, fc.nat(), (text, index) => {
        const bounded = Math.min(index, codePointLength(text));
        const characters = Array.from(text);
        const expected = characters
          .slice(0, bounded)
          .reduce((length, character) => length + character.length, 0);
        return utf16IndexFromCodePoint(text, bounded) === expected;
      }),
      propertyParameters,
    );
  });
});
