import { ApiError } from "./api";
import type { ApprovalItem } from "./contract/panel.gen";
import type { LoadPhase } from "./phase";

export function castInitials(name: string): string {
  const words = name.trim().split(/\s+/).filter(Boolean);
  if (words.length === 0) return "?";
  const first = words[0]?.charAt(0) ?? "";
  const second = words.length > 1 ? (words[1]?.charAt(0) ?? "") : "";
  return `${first}${second}`.toUpperCase();
}

export function castStateNote(phase: LoadPhase): string {
  if (phase === "loading") return "Carregando elenco…";
  if (phase === "not_found") return "Campanha não encontrada.";
  if (phase === "unavailable") return "O vault está indisponível.";
  if (phase === "failed") return "Não foi possível carregar o elenco.";
  return "";
}

export function approvalOwner(item: ApprovalItem): string {
  return item.owner_name ?? item.owner ?? "Sem dono";
}

export function creationNote(error: unknown): string {
  return codeNote(
    error,
    {
      sheet_already_exists: "Você já tem um personagem em análise.",
      character_exists: "Já existe um personagem com esse nome.",
      invalid_payload: "Confira o nome do personagem.",
      vault_write_failed: "Não foi possível gravar no vault.",
    },
    "Não foi possível criar o personagem.",
  );
}

export function decisionNote(error: unknown): string {
  return codeNote(
    error,
    {
      sheet_not_pending: "Esta ficha não está aguardando aprovação.",
      approval_already_decided: "Esta ficha já foi decidida.",
      vault_write_failed:
        "Não foi possível gravar no vault. A ficha continua pendente.",
      invalid_payload: "Confira a nota da recusa.",
    },
    "Não foi possível decidir a aprovação.",
  );
}

export function submitNote(error: unknown): string {
  return codeNote(
    error,
    {
      sheet_not_pending: "Esta ficha não está aguardando aprovação.",
      forbidden: "Só o dono pode reenviar a ficha.",
      vault_write_failed: "Não foi possível gravar no vault.",
    },
    "Não foi possível reenviar a ficha.",
  );
}

function codeNote(
  error: unknown,
  messages: Record<string, string>,
  fallback: string,
): string {
  if (error instanceof ApiError) {
    const message = messages[error.code];
    if (message) return message;
  }
  return fallback;
}
