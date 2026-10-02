import { describe, expect, it } from "vitest";
import {
  nextLoopMode,
  pointerRatio,
  seekDisplayRatio,
  seekTarget,
  volumeGain,
  volumePosition,
} from "./transport.js";

describe("pointerRatio", () => {
  it("maps a pointer x to a clamped 0-1 ratio", () => {
    expect(pointerRatio(50, 200)).toBe(0.25);
    expect(pointerRatio(-10, 200)).toBe(0);
    expect(pointerRatio(500, 200)).toBe(1);
  });

  it("falls back to 0 without a measurable track", () => {
    expect(pointerRatio(50, 0)).toBe(0);
    expect(pointerRatio(50, NaN)).toBe(0);
    expect(pointerRatio(NaN, 200)).toBe(0);
  });
});

describe("seekTarget", () => {
  it("turns a ratio into absolute seconds", () => {
    expect(seekTarget(0.5, 120)).toBe(60);
    expect(seekTarget(1, 120)).toBe(120);
    expect(seekTarget(0, 120)).toBe(0);
  });

  it("clamps a stray ratio and guards an unknown duration", () => {
    expect(seekTarget(2, 120)).toBe(120);
    expect(seekTarget(-1, 120)).toBe(0);
    expect(seekTarget(0.5, 0)).toBe(0);
    expect(seekTarget(0.5, NaN)).toBe(0);
    expect(seekTarget(NaN, 120)).toBe(0);
  });
});

describe("seekDisplayRatio", () => {
  it("holds the pointer preview while dragging", () => {
    expect(seekDisplayRatio(true, 0.3, 0.9)).toBe(0.3);
    expect(seekDisplayRatio(true, 0.3, 0.1)).toBe(0.3);
  });

  it("follows the server ratio when not dragging", () => {
    expect(seekDisplayRatio(false, 0.3, 0.9)).toBe(0.9);
    expect(seekDisplayRatio(false, 0.3, 0.1)).toBe(0.1);
  });

  it("clamps both ratios to 0-1", () => {
    expect(seekDisplayRatio(true, 2, 0)).toBe(1);
    expect(seekDisplayRatio(true, -1, 0)).toBe(0);
    expect(seekDisplayRatio(false, 0, 2)).toBe(1);
    expect(seekDisplayRatio(false, 0, -1)).toBe(0);
  });
});

describe("volume mapping", () => {
  it("squares position into linear gain", () => {
    expect(volumeGain(1)).toBe(1);
    expect(volumeGain(0.5)).toBeCloseTo(0.25);
    expect(volumeGain(0)).toBe(0);
  });

  it("inverts gain back to position", () => {
    expect(volumePosition(0.25)).toBeCloseTo(0.5);
    expect(volumePosition(1)).toBe(1);
    expect(volumePosition(0)).toBe(0);
  });

  it("clamps out-of-range and non-finite input", () => {
    expect(volumeGain(2)).toBe(1);
    expect(volumeGain(-1)).toBe(0);
    expect(volumeGain(NaN)).toBe(0);
    expect(volumePosition(4)).toBe(1);
    expect(volumePosition(NaN)).toBe(0);
  });

  it("round-trips a layer gain through its slider position", () => {
    const positions = [0.7, 0.4, 0.15].map(volumePosition);

    expect(positions[0]).toBeCloseTo(Math.sqrt(0.7));
    expect(positions[0]).not.toBe(0.7);
    for (const [gain, position] of [
      [0.7, positions[0]],
      [0.4, positions[1]],
      [0.15, positions[2]],
    ]) {
      expect(volumeGain(position)).toBeCloseTo(gain);
    }
  });
});

describe("nextLoopMode", () => {
  it("cycles off -> track -> queue -> off", () => {
    expect(nextLoopMode("OFF")).toBe("track");
    expect(nextLoopMode("TRACK")).toBe("queue");
    expect(nextLoopMode("QUEUE")).toBe("off");
  });

  it("falls back to off for an unknown mode", () => {
    expect(nextLoopMode("SOMETHING")).toBe("off");
    expect(nextLoopMode(null)).toBe("off");
  });
});
