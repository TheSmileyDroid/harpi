import { describe, expect, it } from "vitest";
import { ApiError } from "./api";
import { castInitials, castPhaseForError, castStateNote } from "./cast";

describe("castInitials", () => {
  it("takes the first letter of the first two words", () => {
    expect(castInitials("Ana Vhal")).toBe("AV");
    expect(castInitials("Ana")).toBe("A");
  });

  it("ignores extra spacing and empty names", () => {
    expect(castInitials("  Ana   da Casa  ")).toBe("AD");
    expect(castInitials("   ")).toBe("?");
  });
});

describe("castStateNote", () => {
  it("writes the state in Portuguese", () => {
    expect(castStateNote("loading")).toBe("Carregando elenco…");
    expect(castStateNote("not_found")).toBe("Campanha não encontrada.");
    expect(castStateNote("unavailable")).toBe("O vault está indisponível.");
    expect(castStateNote("failed")).toBe("Não foi possível carregar o elenco.");
  });

  it("has no note once the cast is ready", () => {
    expect(castStateNote("ready")).toBe("");
  });
});

describe("castPhaseForError", () => {
  function failure(code: string, status: number): ApiError {
    return new ApiError({ code, message: "Failed", status });
  }

  it("reads a missing campaign as not found", () => {
    expect(castPhaseForError(failure("not_found", 404))).toBe("not_found");
  });

  it("reads a missing vault as unavailable", () => {
    expect(castPhaseForError(failure("vault_unavailable", 503))).toBe(
      "unavailable",
    );
  });

  it("reads anything else as a failure", () => {
    expect(castPhaseForError(failure("internal_error", 500))).toBe("failed");
    expect(castPhaseForError(new Error("offline"))).toBe("failed");
  });
});
