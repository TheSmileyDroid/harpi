import { describe, expect, it } from "vitest";
import { ApiError } from "./api";
import {
  sceneCreationNote,
  sceneOriginLabel,
  sceneSavedLabel,
  sceneStateNote,
} from "./scenes";

describe("scene labels", () => {
  it("names the two scene origins", () => {
    expect(sceneOriginLabel("image")).toBe("Imagem");
    expect(sceneOriginLabel("sketch")).toBe("Desenho");
  });

  it("speaks the saved state", () => {
    expect(sceneSavedLabel(true)).toBe("Salvo");
    expect(sceneSavedLabel(false)).toBe("Alterado no disco");
  });

  it("explains each load phase", () => {
    expect(sceneStateNote("loading")).toBe("Carregando cenas…");
    expect(sceneStateNote("not_found")).toBe("Campanha não encontrada.");
    expect(sceneStateNote("unavailable")).toBe("O vault está indisponível.");
    expect(sceneStateNote("failed")).toBe(
      "Não foi possível carregar as cenas.",
    );
    expect(sceneStateNote("ready")).toBe("");
  });

  it("explains a refused creation by its code", () => {
    const note = (code: string) =>
      sceneCreationNote(new ApiError({ code, message: code, status: 422 }));

    expect(note("scene_exists")).toBe("Já existe uma cena com esse nome.");
    expect(note("invalid_payload")).toBe("Confira o nome e a imagem da cena.");
    expect(note("vault_write_failed")).toBe(
      "Não foi possível gravar no vault.",
    );
    expect(note("vault_unavailable")).toBe("O vault está indisponível.");
    expect(sceneCreationNote(new Error("boom"))).toBe(
      "Não foi possível criar a cena.",
    );
  });
});
