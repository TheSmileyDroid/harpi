import { describe, expect, it } from "vitest";
import {
  formatCount,
  formatDuration,
  formatSeen,
  formatVolume,
} from "./format";

describe("formatCount", () => {
  it("uses the singular for one and the plural otherwise", () => {
    expect(formatCount(0, "faixa", "faixas")).toBe("0 faixas");
    expect(formatCount(1, "faixa", "faixas")).toBe("1 faixa");
    expect(formatCount(4, "faixa", "faixas")).toBe("4 faixas");
  });

  it("takes an explicit plural", () => {
    expect(formatCount(1, "camada", "camadas")).toBe("1 camada");
    expect(formatCount(3, "camada", "camadas")).toBe("3 camadas");
  });
});

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

describe("formatSeen", () => {
  const now = 1_700_000_060_000;

  it("marks a fresh heartbeat as now", () => {
    expect(formatSeen(1_700_000_055, now)).toBe("agora");
  });

  it("counts seconds and minutes since the last heartbeat", () => {
    expect(formatSeen(1_700_000_020, now)).toBe("há 40s");
    expect(formatSeen(1_699_999_800, now)).toBe("há 4min");
  });

  it("falls back for a missing timestamp", () => {
    expect(formatSeen(null, now)).toBe("desconhecido");
    expect(formatSeen(0, now)).toBe("desconhecido");
  });
});
