import { ApiError } from "./api";
import type { SheetConflictField } from "./contract/panel.gen";

export type SheetDecision = "ours" | "theirs" | "both";

const LIST_LABELS: Record<string, string> = {
  aspects: "Aspecto",
  skills: "Perícia",
  stunts: "Façanha",
  stress: "Estresse",
  consequences: "Consequência",
  extras: "Extra",
  inventory: "Inventário",
};

const FIXED_LABELS: Record<string, string> = {
  history: "História",
  notes: "Anotações",
  "block.refresh": "Recarga",
  "block.fate_points": "Pontos de destino",
  "frontmatter.harpi-status": "Status",
};

export function conflictLabel(fieldPath: string): string {
  const fixed = FIXED_LABELS[fieldPath];
  if (fixed) return fixed;
  const box = /^block\.stress\[(.*)\]\.box\[(\d+)\]$/.exec(fieldPath);
  if (box) return `Estresse ${box[1]} · caixa ${box[2]}`;
  const item = /^block\.([a-z_]+)\[(.*)\]$/.exec(fieldPath);
  if (!item) return fieldPath;
  const name = LIST_LABELS[item[1] ?? ""] ?? item[1] ?? "";
  const key = (item[2] ?? "").replace(/\|/g, " · ").replace(/#(\d+)$/, " ($1)");
  return `${name} ${key}`;
}

export function conflictValue(value: string | null): string {
  return value === null || value === "" ? "—" : value;
}

export function conflictNote(error: unknown): string {
  if (error instanceof ApiError) {
    const messages: Record<string, string> = {
      invalid_decision: "Manter os dois só vale para item de lista.",
      conflict_not_pending: "Este conflito já foi decidido.",
      sheet_conflict:
        "A ficha mudou de novo no disco. Recarregue e decida outra vez.",
      forbidden: "Só o dono e o narrador decidem.",
    };
    const message = messages[error.code];
    if (message) return message;
  }
  return "Não foi possível decidir o conflito.";
}

export function conflictsForSheet(
  conflicts: SheetConflictField[],
  sheetId: string | undefined,
): SheetConflictField[] {
  if (!sheetId) return [];
  return conflicts.filter((conflict) => conflict.sheet_id === sheetId);
}
