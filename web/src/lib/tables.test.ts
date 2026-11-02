import { describe, expect, it } from "vitest";
import { ApiError } from "./api";
import {
  canEndTurn,
  canPassTurn,
  gridColumns,
  mapMinWidth,
  nextPendingId,
  ownsTurn,
  rectPath,
  rectsPath,
  tableRoleLabel,
  tableRoundLabel,
  tableSpectatorsLabel,
  tableStateNote,
  tableTurnNote,
  tokenBox,
  tokenIsPublic,
  zoneContains,
  zoneLabelPoint,
  zonePath,
} from "./tables";
import type {
  SceneZone,
  TableParticipant,
  TableScene,
  TableToken,
  TableTurn,
} from "./contract/panel.gen";

const grid = { cell_px: 70, offset_x: 0, offset_y: 0, visible: true };

const scene: TableScene = {
  id: "scn_1",
  slug: "cripta",
  name: "Cripta",
  source: "image",
  width: 800,
  height: 600,
  grid,
  fog_outside: true,
  zones: [],
  fog: [],
  map_url: "/api/tables/tbl_1/map",
  saved: true,
};

function token(overrides: Partial<TableToken> = {}): TableToken {
  return {
    id: "tok_1",
    character_id: null,
    label: "Ana",
    owner_id: null,
    x: 2,
    y: 2,
    w: 1,
    h: 1,
    color: "#e9dfc7",
    visible: true,
    rev: 1,
    ...overrides,
  };
}

function zone(overrides: Partial<SceneZone> = {}): SceneZone {
  return {
    id: "zon_sala",
    label: "Sala",
    revealed: false,
    rects: [{ x: 1, y: 2, w: 3, h: 2 }],
    ...overrides,
  };
}

describe("table labels", () => {
  it("names every role", () => {
    expect(tableRoleLabel("narrator")).toBe("Narrador");
    expect(tableRoleLabel("player")).toBe("Jogador");
    expect(tableRoleLabel("pending")).toBe("Pendente");
    expect(tableRoleLabel("spectator")).toBe("Espectador");
  });

  it("writes the round and the spectator flag", () => {
    expect(tableRoundLabel(3)).toBe("Rodada 3");
    expect(tableSpectatorsLabel(true)).toBe("Aberta");
    expect(tableSpectatorsLabel(false)).toBe("Fechada");
  });

  it("notes the load state", () => {
    expect(tableStateNote("loading")).toContain("Carregando");
    expect(tableStateNote("not_found")).toContain("não encontrada");
    expect(tableStateNote("ready")).toBe("");
  });
});

describe("table geometry", () => {
  it("counts the columns of a scene", () => {
    expect(gridColumns(scene)).toBe(12);
    expect(mapMinWidth(scene, 32)).toBe("384px");
  });

  it("puts a one-cell token at the top-left corner in percent", () => {
    expect(tokenBox(token({ x: 0, y: 0 }), scene)).toEqual({
      left: 0,
      top: 0,
      width: (70 / 800) * 100,
      height: (70 / 600) * 100,
    });
  });

  it("offsets the token by its cell and size", () => {
    const box = tokenBox(token({ x: 2, y: 3, w: 2, h: 1 }), scene);

    expect(box.left).toBeCloseTo((140 / 800) * 100);
    expect(box.top).toBeCloseTo((210 / 600) * 100);
    expect(box.width).toBeCloseTo((140 / 800) * 100);
  });

  it("keeps the token centre inside its half-open zone", () => {
    expect(zoneContains(zone(), 2.5, 2.5)).toBe(true);
    expect(zoneContains(zone(), 4, 2.5)).toBe(false);
  });

  it("hides a token inside a hidden zone", () => {
    expect(tokenIsPublic(token(), [zone()], false)).toBe(false);
  });

  it("shows a token inside a revealed zone", () => {
    expect(tokenIsPublic(token(), [zone({ revealed: true })], true)).toBe(true);
  });

  it("shows a token outside every zone only when fog is off", () => {
    expect(tokenIsPublic(token({ x: 0, y: 0 }), [zone()], true)).toBe(false);
    expect(tokenIsPublic(token({ x: 0, y: 0 }), [zone()], false)).toBe(true);
  });

  it("hides an invisible token even in a revealed zone", () => {
    expect(
      tokenIsPublic(
        token({ visible: false }),
        [zone({ revealed: true })],
        false,
      ),
    ).toBe(false);
  });

  it("draws a zone rectangle in image pixels", () => {
    expect(rectPath({ x: 1, y: 2, w: 3, h: 2 }, grid)).toBe(
      "M 70 140 h 210 v 140 h -210 Z",
    );
    expect(zonePath(zone(), grid)).toBe("M 70 140 h 210 v 140 h -210 Z");
    expect(rectsPath([{ x: 0, y: 0, w: 1, h: 1 }], grid)).toBe(
      "M 0 0 h 70 v 70 h -70 Z",
    );
  });

  it("puts the zone label at the centre of its bounding box", () => {
    expect(zoneLabelPoint(zone(), grid)).toEqual({ x: 175, y: 210 });
  });
});

function participant(
  overrides: Partial<TableParticipant> = {},
): TableParticipant {
  return {
    token_id: "tok_1",
    character_id: null,
    label: "Ana",
    owner_id: null,
    acted: false,
    ...overrides,
  };
}

function turn(overrides: Partial<TableTurn> = {}): TableTurn {
  return {
    id: "trn_1",
    round: 1,
    token_id: "tok_1",
    character_id: null,
    label: "Ana",
    owner_id: "555",
    started_at: 1,
    ...overrides,
  };
}

describe("table turns", () => {
  it("lists who has not acted yet", () => {
    const participants = [
      participant({ token_id: "tok_1", acted: true }),
      participant({ token_id: "tok_2", label: "Bob" }),
      participant({ token_id: "tok_3", label: "Cid" }),
    ];

    expect(nextPendingId(participants, turn())).toBe("tok_2");
    expect(nextPendingId(participants, null)).toBe("tok_2");
  });

  it("recognises the player of the turn from the token owner", () => {
    const participants = [
      participant({ token_id: "tok_1", owner_id: "555", acted: true }),
      participant({ token_id: "tok_2", label: "Bob", owner_id: "777" }),
    ];

    expect(ownsTurn(turn(), "555")).toBe(true);
    expect(ownsTurn(turn(), "777")).toBe(false);
    expect(canEndTurn("player", turn(), "555")).toBe(true);
    expect(canEndTurn("player", turn(), "777")).toBe(false);
    expect(canEndTurn("narrator", turn(), "100")).toBe(true);
    expect(canPassTurn("player", participants, turn(), "555")).toBe(true);
    expect(canPassTurn("player", participants, turn(), "777")).toBe(false);
    expect(canPassTurn("narrator", participants, turn(), "100")).toBe(true);
  });

  it("cannot pass when there is no turn or nobody is pending", () => {
    const lone = [participant({ acted: true })];

    expect(canPassTurn("narrator", lone, null, "100")).toBe(false);
    expect(canPassTurn("narrator", lone, turn(), "100")).toBe(false);
    expect(canEndTurn("narrator", null, "100")).toBe(false);
  });

  it("keeps the waiting turn owned while its token is hidden", () => {
    const hidden = turn({ token_id: "tok_9", owner_id: "555" });
    const pending = [participant({ token_id: "tok_2", label: "Bob" })];

    expect(ownsTurn(hidden, "555")).toBe(true);
    expect(canEndTurn("player", hidden, "555")).toBe(true);
    expect(canPassTurn("player", pending, hidden, "555")).toBe(true);
  });

  it("notes the turn failures in Portuguese", () => {
    expect(
      tableTurnNote(
        new ApiError({ code: "turn_taken", message: "m", status: 422 }),
      ),
    ).toBe("Esse participante já agiu nesta rodada.");
    expect(tableTurnNote(new Error("boom"))).toBe(
      "Não foi possível mudar o turno.",
    );
  });
});
