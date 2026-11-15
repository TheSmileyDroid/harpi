import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { createDebouncer } from "./debounce";

describe("createDebouncer", () => {
  beforeEach(() => {
    vi.useFakeTimers();
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it("runs the latest call once after the delay", () => {
    const debouncer = createDebouncer(300);
    let calls = 0;

    debouncer.run(() => (calls += 1));
    debouncer.run(() => (calls += 1));
    debouncer.run(() => (calls += 1));

    expect(calls).toBe(0);
    vi.advanceTimersByTime(299);
    expect(calls).toBe(0);
    vi.advanceTimersByTime(1);

    expect(calls).toBe(1);
  });

  it("drops a scheduled call on cancel", () => {
    const debouncer = createDebouncer(300);
    let calls = 0;

    debouncer.run(() => (calls += 1));
    debouncer.cancel();
    vi.advanceTimersByTime(1000);

    expect(calls).toBe(0);
  });
});
