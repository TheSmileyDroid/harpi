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
