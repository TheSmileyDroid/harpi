import { describe, expect, it } from "vitest";
import { ApiError } from "./api";
import {
  conflictLabel,
  conflictNote,
  conflictValue,
  conflictsForSheet,
} from "./conflicts";
import type { SheetConflictField } from "./contract/panel.gen";

const CONFLICT: SheetConflictField = {
  id: "cnf_1",
  sheet_id: "sht_ana",
  character_id: "chr_ana",
  field_path: "block.refresh",
  base: "7",
  ours: "9",
  theirs: "4",
  allow_both: false,
};

describe("conflict labels", () => {
  it("names the prose, scalar and status fields", () => {
    expect(conflictLabel("history")).toBe("História");
    expect(conflictLabel("notes")).toBe("Anotações");
    expect(conflictLabel("block.refresh")).toBe("Recarga");
    expect(conflictLabel("block.fate_points")).toBe("Pontos de destino");
    expect(conflictLabel("frontmatter.harpi-status")).toBe("Status");
  });

  it("names a list item by its label", () => {
    expect(conflictLabel("block.aspects[Conceito]")).toBe("Aspecto Conceito");
    expect(conflictLabel("block.consequences[Leve]")).toBe("Consequência Leve");
    expect(conflictLabel("block.extras[Noética|Constructo]")).toBe(
      "Extra Noética · Constructo",
    );
    expect(conflictLabel("block.aspects[Aspecto#2]")).toBe(
      "Aspecto Aspecto (2)",
    );
  });

  it("falls back to the raw path", () => {
    expect(conflictLabel("block.unknown")).toBe("block.unknown");
  });
});

describe("conflict values", () => {
  it("renders an absent side as a dash", () => {
    expect(conflictValue(null)).toBe("—");
    expect(conflictValue("")).toBe("—");
    expect(conflictValue("Piloto")).toBe("Piloto");
  });
});

describe("conflict notes", () => {
  it("explains the decision codes in Portuguese", () => {
    expect(
      conflictNote(
        new ApiError({
          code: "invalid_decision",
          message: "nope",
          status: 422,
        }),
      ),
    ).toContain("item de lista");
    expect(
      conflictNote(
        new ApiError({
          code: "conflict_not_pending",
          message: "",
          status: 409,
        }),
      ),
    ).toContain("já foi decidido");
  });

  it("falls back for an unknown failure", () => {
    expect(conflictNote(new Error("boom"))).toContain("Não foi possível");
  });
});

describe("conflicts for a sheet", () => {
  it("keeps only the conflicts of the chosen sheet", () => {
    expect(conflictsForSheet([CONFLICT], "sht_ana")).toEqual([CONFLICT]);
    expect(conflictsForSheet([CONFLICT], "sht_other")).toEqual([]);
    expect(conflictsForSheet([CONFLICT], undefined)).toEqual([]);
  });
});
