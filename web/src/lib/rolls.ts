import { codeNote } from "./errors";
import type { TableRoll } from "./contract/panel.gen";

export function rollSourceLabel(source: TableRoll["source"]): string {
  return source === "panel" ? "PAINEL" : "DISCORD";
}

export function rollMessage(roll: TableRoll): string {
  const scene = roll.scene_label ? ` · ${roll.scene_label}` : "";
  return `${roll.actor_label}${scene} — ${roll.text}`;
}

function compareRolls(left: TableRoll, right: TableRoll): number {
  if (left.created_at !== right.created_at) {
    return left.created_at - right.created_at;
  }
  if (left.id === right.id) return 0;
  return left.id < right.id ? -1 : 1;
}

export function mergeRolls(
  current: TableRoll[],
  incoming: TableRoll[],
): TableRoll[] {
  const byId = new Map(current.map((roll) => [roll.id, roll]));
  for (const roll of incoming) byId.set(roll.id, roll);
  return [...byId.values()].sort(compareRolls);
}

export function rollCursor(rolls: TableRoll[]): string | null {
  return rolls.at(-1)?.id ?? null;
}

export function rollNote(error: unknown): string {
  return codeNote(
    error,
    {
      bad_cursor: "O log precisa ser recarregado.",
      discord_unavailable: "O Discord está fora; a rolagem não foi registrada.",
      expression_too_long: "A expressão vai até 120 caracteres.",
      forbidden: "Seu papel não rola nesta mesa.",
      invalid_expression: "A expressão de dados não é válida.",
      no_dice: "A expressão precisa de dados.",
      non_integer_result: "O resultado precisa ser inteiro.",
      result_too_large: "O resultado da rolagem é grande demais.",
      result_too_long: "A rolagem passou do limite de 2000 caracteres.",
      table_closed: "A mesa está fechada.",
      too_many_dice: "Um grupo de dados vai até 20.",
      too_many_repeats: "A repetição vai até 10 rolagens.",
      too_many_requests: "Muitas rolagens em pouco tempo.",
    },
    "Não foi possível rolar.",
  );
}
