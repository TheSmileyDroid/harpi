import { ApiError } from "./api";

export type CastPhase =
  "loading" | "ready" | "not_found" | "unavailable" | "failed";

export function castInitials(name: string): string {
  const words = name.trim().split(/\s+/).filter(Boolean);
  if (words.length === 0) return "?";
  const first = words[0]?.charAt(0) ?? "";
  const second = words.length > 1 ? (words[1]?.charAt(0) ?? "") : "";
  return `${first}${second}`.toUpperCase();
}

export function castStateNote(phase: CastPhase): string {
  if (phase === "loading") return "Carregando elenco…";
  if (phase === "not_found") return "Campanha não encontrada.";
  if (phase === "unavailable") return "O vault está indisponível.";
  if (phase === "failed") return "Não foi possível carregar o elenco.";
  return "";
}

export function castPhaseForError(error: unknown): CastPhase {
  if (error instanceof ApiError) {
    if (error.code === "vault_unavailable") return "unavailable";
    if (error.status === 404) return "not_found";
  }
  return "failed";
}
