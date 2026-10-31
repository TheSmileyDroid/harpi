import { describe, expect, it } from "vitest";
import {
  SHELL_PAGES,
  campaignDisplayName,
  isShellPageActive,
  shellLinkLabel,
} from "./shell";

describe("SHELL_PAGES", () => {
  it("lists the four campaign pages in order", () => {
    expect(SHELL_PAGES.map((page) => page.slug)).toEqual([
      "mesa",
      "personagens",
      "ficha",
      "cenas",
    ]);
  });

  it("points each page at its campaign route", () => {
    expect(SHELL_PAGES.map((page) => page.route)).toEqual([
      "/c/[campaign]/mesa",
      "/c/[campaign]/personagens",
      "/c/[campaign]/ficha/[[character]]",
      "/c/[campaign]/cenas",
    ]);
  });
});

describe("isShellPageActive", () => {
  it("marks the matching campaign page", () => {
    expect(isShellPageActive("/c/paratheos/mesa", "mesa")).toBe(true);
    expect(isShellPageActive("/c/paratheos/cenas/cripta", "cenas")).toBe(true);
  });

  it("leaves the other pages and the music page unmarked", () => {
    expect(isShellPageActive("/c/paratheos/mesa", "ficha")).toBe(false);
    expect(isShellPageActive("/", "mesa")).toBe(false);
    expect(isShellPageActive("/c/paratheos", "mesa")).toBe(false);
  });
});

describe("campaignDisplayName", () => {
  it("reads the slug as a display name", () => {
    expect(campaignDisplayName("paratheos")).toBe("Paratheos");
    expect(campaignDisplayName("the-hollow")).toBe("The Hollow");
  });

  it("keeps an empty slug empty", () => {
    expect(campaignDisplayName("")).toBe("");
  });
});

describe("shellLinkLabel", () => {
  it("names each link state", () => {
    expect(shellLinkLabel("connecting")).toBe("Conectando");
    expect(shellLinkLabel("connected")).toBe("Ativo");
    expect(shellLinkLabel("reconnecting")).toBe("Perdido");
  });
});
