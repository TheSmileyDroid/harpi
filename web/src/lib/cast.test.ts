import { describe, expect, it } from "vitest";
import { castInitials, castStateNote } from "./cast";

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
