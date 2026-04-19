import { describe, expect, test } from "vitest";
import { fnum, fint, MODE_LABELS } from "../radio";

describe("fnum", () => {
  test("parses valid number", () => {
    expect(fnum("42.5", 0)).toBe(42.5);
  });

  test("falls back to default on invalid", () => {
    expect(fnum("abc", 10)).toBe(10);
  });

  test("falls back to default on empty string", () => {
    expect(fnum("", 99)).toBe(99);
  });

  test("trims whitespace", () => {
    expect(fnum("  3.14  ", 0)).toBe(3.14);
  });

  test("handles negative numbers", () => {
    expect(fnum("-100", 0)).toBe(-100);
  });

  test("handles zero", () => {
    expect(fnum("0", 1)).toBe(0);
  });
});

describe("fint", () => {
  test("parses valid integer", () => {
    expect(fint("2", 0)).toBe(2);
  });

  test("rounds float to integer", () => {
    expect(fint("2.7", 0)).toBe(3);
  });

  test("falls back on invalid", () => {
    expect(fint("", 1)).toBe(1);
  });

  test("falls back on NaN string", () => {
    expect(fint("abc", 5)).toBe(5);
  });

  test("handles negative", () => {
    expect(fint("-5", 0)).toBe(-5);
  });
});

describe("MODE_LABELS", () => {
  test("has labels for modes 0-5", () => {
    for (let i = 0; i <= 5; i++) {
      expect(MODE_LABELS[i]).toBeTruthy();
    }
  });

  test("has exactly 6 modes", () => {
    expect(Object.keys(MODE_LABELS)).toHaveLength(6);
  });
});