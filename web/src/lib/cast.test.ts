import { describe, expect, it } from "vitest";
import { ApiError } from "./api";
import {
  approvalOwner,
  castInitials,
  castStateNote,
  creationNote,
  decisionNote,
  submitNote,
} from "./cast";
import fixtures from "./contract/fixtures/fixtures.json";

const APPROVAL = fixtures.ApprovalList.approvals[0]!;

function apiError(code: string): ApiError {
  return new ApiError({ code, message: "m", status: 409 });
}

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

describe("approvalOwner", () => {
  it("prefers the display name over the snowflake", () => {
    expect(approvalOwner(APPROVAL)).toBe("Harpi");
  });

  it("falls back to the snowflake and then to a label", () => {
    expect(approvalOwner({ ...APPROVAL, owner_name: null })).toBe("555");
    expect(approvalOwner({ ...APPROVAL, owner_name: null, owner: null })).toBe(
      "Sem dono",
    );
  });
});

describe("creationNote", () => {
  it("explains the conflict codes in Portuguese", () => {
    expect(creationNote(apiError("sheet_already_exists"))).toBe(
      "Você já tem um personagem em análise.",
    );
    expect(creationNote(apiError("character_exists"))).toBe(
      "Já existe um personagem com esse nome.",
    );
    expect(creationNote(apiError("invalid_payload"))).toBe(
      "Confira o nome do personagem.",
    );
    expect(creationNote(apiError("vault_write_failed"))).toBe(
      "Não foi possível gravar no vault.",
    );
  });

  it("falls back to a generic note", () => {
    expect(creationNote(new Error("boom"))).toBe(
      "Não foi possível criar o personagem.",
    );
  });
});

describe("decisionNote", () => {
  it("explains the decision failures in Portuguese", () => {
    expect(decisionNote(apiError("sheet_not_pending"))).toBe(
      "Esta ficha não está aguardando aprovação.",
    );
    expect(decisionNote(apiError("approval_already_decided"))).toBe(
      "Esta ficha já foi decidida.",
    );
    expect(decisionNote(apiError("vault_write_failed"))).toBe(
      "Não foi possível gravar no vault. A ficha continua pendente.",
    );
    expect(decisionNote(apiError("invalid_payload"))).toBe(
      "Confira a nota da recusa.",
    );
  });

  it("falls back to a generic note", () => {
    expect(decisionNote("nope")).toBe("Não foi possível decidir a aprovação.");
  });
});

describe("submitNote", () => {
  it("explains the resubmit failures in Portuguese", () => {
    expect(submitNote(apiError("sheet_not_pending"))).toBe(
      "Esta ficha não está aguardando aprovação.",
    );
    expect(submitNote(apiError("forbidden"))).toBe(
      "Só o dono pode reenviar a ficha.",
    );
    expect(submitNote(apiError("vault_write_failed"))).toBe(
      "Não foi possível gravar no vault.",
    );
  });

  it("falls back to a generic note", () => {
    expect(submitNote("nope")).toBe("Não foi possível reenviar a ficha.");
  });
});
