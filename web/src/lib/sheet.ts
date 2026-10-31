import type {
  SheetDetail,
  SheetLadderStep,
  SheetSkill,
} from "./contract/panel.gen";
import type { LoadPhase } from "./phase";

type SheetStatus = SheetDetail["status"];

interface SkillGroup {
  rank: number;
  label: string;
  skills: SheetSkill[];
}

export function sheetStateNote(phase: LoadPhase): string {
  if (phase === "loading") return "Carregando ficha…";
  if (phase === "not_found") return "Ficha não encontrada.";
  if (phase === "unavailable") return "O vault está indisponível.";
  if (phase === "failed") return "Não foi possível carregar a ficha.";
  return "";
}

export function itemLabel(item: string): string {
  const match = item.match(/\[\[([^\]|]+)(?:\|[^\]]*)?\]\]/);
  return (match?.[1] ?? item).trim();
}

export function statusLabel(status: SheetStatus): string {
  if (status === "active") return "Ativa";
  if (status === "pending") return "Pendente";
  return "Arquivada";
}

export function skillsByRank(
  skills: SheetSkill[],
  ladder: SheetLadderStep[],
): SkillGroup[] {
  return ladder
    .map((step) => ({
      rank: step.rank,
      label: step.label,
      skills: skills.filter((skill) => skill.rank === step.rank),
    }))
    .filter((group) => group.skills.length > 0);
}
