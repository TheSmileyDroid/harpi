import { describe, expect, it } from "vitest";
import type { SheetDetail } from "./contract/panel.gen";
import {
  parseInteger,
  parseOptionalInteger,
  patchBody,
  sheetDraft,
  sheetLocked,
  toggleStress,
  wikilink,
} from "./sheet-edit";

const SHEET: SheetDetail = {
  id: "sht_ana",
  character_id: "chr_ana",
  owner: "555",
  status: "active",
  state: "ok",
  read_only: false,
  error: null,
  hash: "a".repeat(64),
  rev: 3,
  history: "Uma piloto.",
  notes: "Fim.",
  warnings: [],
  refresh: 7,
  fate_points: 3,
  ladder: [{ rank: 4, label: "Ótimo" }],
  aspects: [
    { label: "Conceito", text: "Piloto de carga" },
    { label: "Problema", text: "Sem memória" },
  ],
  skills: [{ name: "Hackear", rank: 4, label: "Ótimo" }],
  stunts: [],
  stress: [
    {
      track: "Físico",
      boxes: [
        { value: 1, checked: false },
        { value: 2, checked: true },
      ],
    },
  ],
  consequences: [{ severity: "Leve", value: 2, text: "Casco rachado" }],
  extras: [
    {
      kind: "Noética",
      name: "Constructo",
      text: "Corpo artificial.",
      cost: 0,
    },
  ],
  inventory: [{ item: "[[Espada de Lancelot]]", qty: 1, note: "Relíquia" }],
};

describe("sheet drafts", () => {
  it("copies the sheet without sharing the arrays", () => {
    const draft = sheetDraft(SHEET);

    draft.aspects[0]!.text = "Outro";

    expect(SHEET.aspects[0]!.text).toBe("Piloto de carga");
    expect(draft.history).toBe("Uma piloto.");
    expect(draft.inventory[0]!.item).toBe("[[Espada de Lancelot]]");
  });

  it("toggles only the chosen stress box", () => {
    const stress = toggleStress(sheetDraft(SHEET), "Físico", 1);

    expect(stress[0]!.boxes).toEqual([
      { value: 1, checked: true },
      { value: 2, checked: true },
    ]);
    expect(stress[0]!.boxes).toHaveLength(2);
  });

  it("builds the patch with the read hash and wikilinks", () => {
    const body = patchBody(SHEET, sheetDraft(SHEET));

    expect(body.base_hash).toBe(SHEET.hash);
    expect(body.inventory?.[0]?.item).toBe("[[Espada de Lancelot]]");
    expect(body.aspects?.[0]).toEqual({
      label: "Conceito",
      text: "Piloto de carga",
    });
    expect(body.history).toBe("Uma piloto.");
    expect(body.notes).toBe("Fim.");
    expect(body.skills).toBeUndefined();
  });

  it("keeps an inventory alias through an unrelated save", () => {
    const sheet = {
      ...SHEET,
      inventory: [{ item: "[[Espada|a boa]]", qty: 1, note: "Relíquia" }],
    };
    const body = patchBody(sheet, sheetDraft(sheet));

    expect(body.inventory?.[0]?.item).toBe("[[Espada|a boa]]");
  });
});

describe("sheet field values", () => {
  it("wraps a plain item in a wikilink", () => {
    expect(wikilink("Corda")).toBe("[[Corda]]");
    expect(wikilink("[[Corda]]")).toBe("[[Corda]]");
    expect(wikilink("  ")).toBe("");
  });

  it("parses integers with a fallback", () => {
    expect(parseInteger("3", 1)).toBe(3);
    expect(parseInteger("", 1)).toBe(1);
    expect(parseOptionalInteger("")).toBeNull();
    expect(parseOptionalInteger("2")).toBe(2);
  });
});

describe("sheet locking", () => {
  it("locks archived, invalid and conflicted sheets", () => {
    expect(sheetLocked(SHEET, false)).toBe(false);
    expect(sheetLocked({ ...SHEET, read_only: true }, false)).toBe(true);
    expect(sheetLocked({ ...SHEET, state: "invalid" }, false)).toBe(true);
    expect(sheetLocked(SHEET, true)).toBe(true);
  });
});
