import { describe, expect, it } from "vitest";
import { get } from "svelte/store";
import { createErrorRegion } from "./errors.js";
import { createToasts } from "./toasts.js";

describe("createErrorRegion", () => {
  it("keeps failures until they are dismissed", () => {
    const region = createErrorRegion();

    const id = region.report({ code: "unauthorized", message: "Nope" });

    expect(get(region)).toHaveLength(1);
    expect(get(region)[0]).toMatchObject({
      code: "unauthorized",
      message: "Nope",
    });

    region.dismiss(id);

    expect(get(region)).toHaveLength(0);
  });

  it("clears every failure", () => {
    const region = createErrorRegion();
    region.report({ code: "a", message: "a" });
    region.report({ code: "b", message: "b" });

    region.clear();

    expect(get(region)).toHaveLength(0);
  });
});

describe("createToasts", () => {
  it("pushes a confirmation and removes it when its time is up", () => {
    const pending = [];
    const toasts = createToasts({ schedule: (fn) => pending.push(fn) });

    toasts.push("Signed in");
    expect(get(toasts)).toHaveLength(1);

    pending[0]();

    expect(get(toasts)).toHaveLength(0);
  });

  it("can dismiss a confirmation early", () => {
    const toasts = createToasts({ schedule: () => {} });

    const id = toasts.push("Signed in");
    toasts.dismiss(id);

    expect(get(toasts)).toHaveLength(0);
  });
});
