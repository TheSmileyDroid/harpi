import { describe, expect, it } from "vitest";
import { formatDuration, formatVolume } from "./format";

describe("formatDuration", () => {
  it("formats minutes and seconds", () => {
    expect(formatDuration(45)).toBe("0:45");
    expect(formatDuration(120)).toBe("2:00");
  });

  it("formats hours", () => {
    expect(formatDuration(3661)).toBe("1:01:01");
  });

  it("falls back for empty or invalid values", () => {
    expect(formatDuration(0)).toBe("0:00");
    expect(formatDuration(-5)).toBe("0:00");
    expect(formatDuration(null)).toBe("0:00");
    expect(formatDuration(undefined)).toBe("0:00");
    expect(formatDuration(NaN)).toBe("0:00");
  });
});

describe("formatVolume", () => {
  it("renders a gain as a percentage", () => {
    expect(formatVolume(0.25)).toBe("25%");
    expect(formatVolume(1)).toBe("100%");
    expect(formatVolume(0)).toBe("0%");
  });

  it("clamps and tolerates invalid values", () => {
    expect(formatVolume(1.5)).toBe("100%");
    expect(formatVolume(-1)).toBe("0%");
    expect(formatVolume(null)).toBe("0%");
    expect(formatVolume(undefined)).toBe("0%");
    expect(formatVolume(NaN)).toBe("0%");
  });
});
