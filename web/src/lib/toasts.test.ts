import { describe, expect, it, vi } from "vitest";
import { get } from "svelte/store";
import { createToasts } from "./toasts";

describe("createToasts", () => {
  it("pushes a toast and expires it on schedule", () => {
    const timers: Array<() => void> = [];
    const toasts = createToasts({
      schedule: (fn) => {
        timers.push(fn);
        return 0;
      },
    });

    toasts.push("Saved");
    expect(get(toasts)).toEqual([{ id: 1, message: "Saved" }]);

    timers[0]!();
    expect(get(toasts)).toEqual([]);
  });

  it("carries an undo action", () => {
    const run = vi.fn();
    const toasts = createToasts({ schedule: () => 0 });

    toasts.push("Removed", { label: "Undo", run });

    const [toast] = get(toasts);
    expect(toast!.action?.label).toBe("Undo");
    toast!.action!.run();
    expect(run).toHaveBeenCalledOnce();
  });

  it("dismisses by id", () => {
    const toasts = createToasts({ schedule: () => 0 });

    const id = toasts.push("One");
    toasts.push("Two");
    toasts.dismiss(id);

    expect(get(toasts).map((toast) => toast.message)).toEqual(["Two"]);
  });
});
