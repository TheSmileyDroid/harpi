import { codeNote } from "./errors";
import type { LoadPhase } from "./phase";
import type { SceneDetail } from "./contract/panel.gen";

export type SceneSource = SceneDetail["source"];

export function sceneOriginLabel(source: SceneSource): string {
  return source === "sketch" ? "Desenho" : "Imagem";
}

export function sceneStateNote(phase: LoadPhase): string {
  if (phase === "loading") return "Carregando cenas…";
  if (phase === "not_found") return "Campanha não encontrada.";
  if (phase === "unavailable") return "O vault está indisponível.";
  if (phase === "failed") return "Não foi possível carregar as cenas.";
  return "";
}

export function sceneSavedLabel(saved: boolean): string {
  return saved ? "Salvo" : "Alterado no disco";
}

export function sceneCreationNote(error: unknown): string {
  return codeNote(
    error,
    {
      scene_exists: "Já existe uma cena com esse nome.",
      invalid_payload: "Confira o nome e a imagem da cena.",
      vault_write_failed: "Não foi possível gravar no vault.",
      vault_unavailable: "O vault está indisponível.",
    },
    "Não foi possível criar a cena.",
  );
}
