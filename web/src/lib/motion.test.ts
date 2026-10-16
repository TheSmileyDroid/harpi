import { afterEach, describe, expect, it, vi } from "vitest";
import { flipParams } from "./motion";

function stubMatchMedia(matches: boolean) {
  vi.stubGlobal("window", { matchMedia: () => ({ matches }) });
}

describe("flipParams", () => {
  afterEach(() => vi.unstubAllGlobals());

  it("settles list rows when movement is allowed", () => {
    stubMatchMedia(false);

    const params = flipParams();

    expect(params.duration).toBe(200);
    expect(typeof params.easing).toBe("function");
  });

  it("drops the movement when the operator asks for reduced motion", () => {
    stubMatchMedia(true);

    expect(flipParams()).toEqual({ duration: 0 });
  });
});
