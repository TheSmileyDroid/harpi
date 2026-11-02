import { describe, expect, it } from "vitest";
import { ApiError } from "./api";
import type { TableRoll } from "./contract/panel.gen";
import {
  mergeRolls,
  rollCursor,
  rollMessage,
  rollNote,
  rollSourceLabel,
} from "./rolls";

function roll(overrides: Partial<TableRoll> = {}): TableRoll {
  return {
    id: "rol_01",
    table_id: "tbl_1",
    scene_id: "scn_1",
    scene_label: "Cripta",
    turn_id: null,
    actor_id: "555",
    actor_label: "Ana",
    source: "panel",
    expression: "4dF",
    total: 1,
    dice: {
      index: 1,
      of: 1,
      expression: "4dF",
      groups: [
        { notation: "4dF", values: [-1, 0, 1, 1], kept: null, total: 1 },
      ],
    },
    text: "` 1 ` ⟵ [ - , , + , + ] 4dF",
    discord_message_id: "123",
    created_at: 100,
    ...overrides,
  };
}

describe("roll labels", () => {
  it("marks the surface that produced the roll", () => {
    expect(rollSourceLabel("panel")).toBe("PAINEL");
    expect(rollSourceLabel("discord")).toBe("DISCORD");
  });

  it("composes author and scene around the frozen body", () => {
    expect(rollMessage(roll())).toBe(
      "Ana · Cripta — ` 1 ` ⟵ [ - , , + , + ] 4dF",
    );
  });

  it("drops the scene segment when there is no scene", () => {
    expect(rollMessage(roll({ scene_label: "" }))).toBe(
      "Ana — ` 1 ` ⟵ [ - , , + , + ] 4dF",
    );
  });
});

describe("roll log", () => {
  it("deduplicates by id and orders by created_at then id", () => {
    const first = roll({ id: "rol_01", created_at: 100 });
    const second = roll({ id: "rol_02", created_at: 100 });
    const later = roll({ id: "rol_00", created_at: 101 });

    expect(
      mergeRolls([second], [later, first, second]).map((r) => r.id),
    ).toEqual(["rol_01", "rol_02", "rol_00"]);
  });

  it("uses the last roll as the recovery cursor", () => {
    expect(rollCursor([])).toBeNull();
    expect(rollCursor([roll({ id: "rol_09" })])).toBe("rol_09");
  });
});

describe("roll notes", () => {
  it("names the failing surface", () => {
    const failure = new ApiError({
      code: "discord_unavailable",
      message: "Discord is unavailable",
      status: 502,
    });
    expect(rollNote(failure)).toContain("Discord está fora");
    expect(rollNote(new Error("boom"))).toBe("Não foi possível rolar.");
  });
});
