import { describe, expect, it } from "vitest";
import { createDebouncer } from "./debounce.js";

function controlledSchedule() {
  const pending = new Map();
  let nextId = 0;
  return {
    pending,
    schedule(fn) {
      const id = ++nextId;
      pending.set(id, fn);
      return id;
    },
    cancel(id) {
      pending.delete(id);
    },
    fire(id) {
      const fn = pending.get(id);
      pending.delete(id);
      fn();
    },
  };
}

describe("createDebouncer", () => {
  it("runs the latest call once after the delay", () => {
    const clock = controlledSchedule();
    const debouncer = createDebouncer({
      delay: 300,
      schedule: clock.schedule,
      cancel: clock.cancel,
    });
    let calls = 0;

    debouncer.run(() => (calls += 1));
    debouncer.run(() => (calls += 1));
    debouncer.run(() => (calls += 1));

    expect(calls).toBe(0);
    expect(clock.pending.size).toBe(1);
    clock.fire([...clock.pending.keys()][0]);

    expect(calls).toBe(1);
  });

  it("drops a scheduled call on cancel", () => {
    const clock = controlledSchedule();
    const debouncer = createDebouncer({
      schedule: clock.schedule,
      cancel: clock.cancel,
    });
    let calls = 0;

    debouncer.run(() => (calls += 1));
    debouncer.cancel();

    expect(clock.pending.size).toBe(0);
    expect(calls).toBe(0);
  });
});
