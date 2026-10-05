import { describe, expect, it } from "vitest";
import { looksLikeUrl } from "./url";

describe("looksLikeUrl", () => {
  it("accepts a pasted http(s) link", () => {
    expect(looksLikeUrl("https://example.com/song")).toBe(true);
    expect(looksLikeUrl("  http://youtu.be/abc  ")).toBe(true);
  });

  it("rejects a text term and a URL with extra words", () => {
    expect(looksLikeUrl("daft punk")).toBe(false);
    expect(looksLikeUrl("https://example.com/song daft punk")).toBe(false);
    expect(looksLikeUrl("")).toBe(false);
  });
});
