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

export function sceneEditorStateNote(phase: LoadPhase): string {
  if (phase === "loading") return "Carregando a cena…";
  if (phase === "not_found") return "Cena ou campanha não encontrada.";
  if (phase === "unavailable") return "O vault está indisponível.";
  if (phase === "failed") return "Não foi possível carregar a cena.";
  return "";
}

export function sceneSaveNote(error: unknown): string {
  return codeNote(
    error,
    {
      scene_conflict: "A cena mudou no disco. Recarregue para importar.",
      scene_unreadable: "O arquivo da cena não pode ser lido.",
      invalid_payload: "Confira as salas e o grid antes de salvar.",
      vault_write_failed: "Não foi possível gravar no vault.",
      vault_unavailable: "O vault está indisponível.",
    },
    "Não foi possível salvar a cena.",
  );
}

export function sceneImageUrl(campaign: string, slug: string): string {
  return `/api/campaigns/${encodeURIComponent(campaign)}/scenes/${encodeURIComponent(slug)}/image`;
}

export function sceneUsageSummary(
  inUse: boolean,
  tokens: number,
  revealed: number,
  total: number,
): string {
  const count = total === 1 ? "área" : "áreas";
  const state = total === 1 ? "revelada" : "reveladas";
  const tokenLabel = tokens === 1 ? "token" : "tokens";
  const prefix = inUse ? "Em uso na mesa" : "Sem mesa";
  const suffix = inUse ? "agora" : "no molde";
  return `${prefix} · ${tokens} ${tokenLabel} · ${revealed} de ${total} ${count} ${state} ${suffix}`;
}
