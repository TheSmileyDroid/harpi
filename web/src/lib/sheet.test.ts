import { describe, expect, it } from "vitest";
import { itemLabel, sheetStateNote, skillsByRank, statusLabel } from "./sheet";

describe("sheet phases", () => {
  it("speaks Portuguese", () => {
    expect(sheetStateNote("loading")).toBe("Carregando ficha…");
    expect(sheetStateNote("not_found")).toBe("Ficha não encontrada.");
    expect(sheetStateNote("unavailable")).toBe("O vault está indisponível.");
    expect(sheetStateNote("failed")).toBe("Não foi possível carregar a ficha.");
    expect(sheetStateNote("ready")).toBe("");
  });
});

describe("item labels", () => {
  it("unwraps a wikilink", () => {
    expect(itemLabel("[[Espada de Lancelot]]")).toBe("Espada de Lancelot");
  });

  it("drops the wikilink alias", () => {
    expect(itemLabel("[[Espada de Lancelot|a relíquia]]")).toBe(
      "Espada de Lancelot",
    );
  });

  it("keeps a dead link as plain text", () => {
    expect(itemLabel("Corda de doze metros")).toBe("Corda de doze metros");
  });
});

describe("sheet status", () => {
  it("labels every status", () => {
    expect(statusLabel("active")).toBe("Ativa");
    expect(statusLabel("pending")).toBe("Pendente");
    expect(statusLabel("archived")).toBe("Arquivada");
  });
});

describe("skills by rank", () => {
  const ladder = [
    { rank: 4, label: "Ótimo" },
    { rank: 3, label: "Bom" },
    { rank: 2, label: "Razoável" },
  ];

  it("groups skills under their ladder step", () => {
    expect(
      skillsByRank(
        [
          { name: "Hackear", rank: 4, label: "Ótimo" },
          { name: "Atirar", rank: 3, label: "Bom" },
          { name: "Luta", rank: 4, label: "Ótimo" },
        ],
        ladder,
      ),
    ).toEqual([
      {
        rank: 4,
        label: "Ótimo",
        skills: [
          { name: "Hackear", rank: 4, label: "Ótimo" },
          { name: "Luta", rank: 4, label: "Ótimo" },
        ],
      },
      {
        rank: 3,
        label: "Bom",
        skills: [{ name: "Atirar", rank: 3, label: "Bom" }],
      },
    ]);
  });

  it("drops empty steps", () => {
    expect(skillsByRank([], ladder)).toEqual([]);
  });
});
