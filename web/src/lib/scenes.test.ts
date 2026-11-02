import { describe, expect, it } from "vitest";
import { ApiError } from "./api";
import {
  sceneCreationNote,
  sceneEditorStateNote,
  sceneImageUrl,
  sceneOriginLabel,
  sceneSaveNote,
  sceneSavedLabel,
  sceneStateNote,
  sceneUsageSummary,
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

  it("points at the scene image route", () => {
    expect(sceneImageUrl("paratheos", "cripta")).toBe(
      "/api/campaigns/paratheos/scenes/cripta/image",
    );
  });

  it("summarizes the use with and without a table", () => {
    expect(sceneUsageSummary(false, 0, 1, 3)).toBe(
      "Sem mesa · 0 tokens · 1 de 3 áreas reveladas no molde",
    );
    expect(sceneUsageSummary(true, 2, 2, 2)).toBe(
      "Em uso na mesa · 2 tokens · 2 de 2 áreas reveladas agora",
    );
    expect(sceneUsageSummary(true, 1, 0, 1)).toBe(
      "Em uso na mesa · 1 token · 0 de 1 área revelada agora",
    );
  });

  it("explains the editor load phases", () => {
    expect(sceneEditorStateNote("loading")).toBe("Carregando a cena…");
    expect(sceneEditorStateNote("not_found")).toBe(
      "Cena ou campanha não encontrada.",
    );
    expect(sceneEditorStateNote("unavailable")).toBe(
      "O vault está indisponível.",
    );
    expect(sceneEditorStateNote("failed")).toBe(
      "Não foi possível carregar a cena.",
    );
    expect(sceneEditorStateNote("ready")).toBe("");
  });

  it("explains a refused save by its code", () => {
    const note = (code: string) =>
      sceneSaveNote(new ApiError({ code, message: code, status: 409 }));

    expect(note("scene_conflict")).toBe(
      "A cena mudou no disco. Recarregue para importar.",
    );
    expect(note("scene_unreadable")).toBe(
      "O arquivo da cena não pode ser lido.",
    );
    expect(note("invalid_payload")).toBe(
      "Confira as salas e o grid antes de salvar.",
    );
    expect(sceneSaveNote(new Error("boom"))).toBe(
      "Não foi possível salvar a cena.",
    );
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
