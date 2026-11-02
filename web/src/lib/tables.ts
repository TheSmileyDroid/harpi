import { codeNote } from "./errors";
import type { LoadPhase } from "./phase";
import type {
  SceneGrid,
  SceneRect,
  SceneZone,
  TableScene,
  TableSummary,
  TableToken,
} from "./contract/panel.gen";

type TableRole = TableSummary["role"];

export function tableRoleLabel(role: TableRole): string {
  if (role === "narrator") return "Narrador";
  if (role === "player") return "Jogador";
  if (role === "spectator") return "Espectador";
  return "Pendente";
}

export function tableStateNote(phase: LoadPhase): string {
  if (phase === "loading") return "Carregando a mesa…";
  if (phase === "not_found") return "Mesa ou campanha não encontrada.";
  if (phase === "unavailable") return "O vault está indisponível.";
  if (phase === "failed") return "Não foi possível carregar a mesa.";
  return "";
}

export function tableRoundLabel(round: number): string {
  return `Rodada ${round}`;
}

export function tableSpectatorsLabel(open: boolean): string {
  return open ? "Aberta" : "Fechada";
}

export function tableOpenNote(error: unknown): string {
  return codeNote(
    error,
    {
      table_already_open:
        "Já existe uma mesa aberta nesta campanha ou neste canal.",
      forbidden: "Só o narrador abre a mesa.",
      invalid_payload: "Confira o canal e a cena escolhida.",
      not_found: "Campanha ou cena não encontrada.",
    },
    "Não foi possível abrir a mesa.",
  );
}

export function tableActionNote(error: unknown): string {
  return codeNote(
    error,
    {
      table_closed: "A mesa está fechada.",
      snapshot_failed: "Não foi possível gravar o snapshot da mesa.",
      scene_unreadable: "O arquivo da cena não pode ser lido.",
      forbidden: "Só o narrador conduz a mesa.",
      not_found: "Mesa, cena ou token não encontrado.",
    },
    "Não foi possível concluir a ação.",
  );
}

export function tableTokenNote(error: unknown): string {
  return codeNote(
    error,
    {
      invalid_payload: "Confira a posição e o tamanho do token.",
      table_closed: "A mesa está fechada.",
      forbidden: "Só o narrador posiciona tokens.",
      not_found: "Token não encontrado.",
    },
    "Não foi possível salvar o token.",
  );
}

export function tableZoneNote(error: unknown): string {
  return codeNote(
    error,
    {
      forbidden: "Só o narrador revela ou cobre áreas.",
      not_found: "Área não encontrada.",
      table_closed: "A mesa está fechada.",
    },
    "Não foi possível mudar a névoa.",
  );
}

function tokenCenter(token: TableToken): { x: number; y: number } {
  return { x: token.x + token.w / 2, y: token.y + token.h / 2 };
}

export function zoneContains(zone: SceneZone, x: number, y: number): boolean {
  return zone.rects.some(
    (rect) =>
      rect.x <= x && x < rect.x + rect.w && rect.y <= y && y < rect.y + rect.h,
  );
}

export function tokenIsPublic(
  token: TableToken,
  zones: SceneZone[],
  fogOutside: boolean,
): boolean {
  if (!token.visible) return false;
  const center = tokenCenter(token);
  const containing = zones.filter((zone) =>
    zoneContains(zone, center.x, center.y),
  );
  if (containing.length > 0) {
    return containing.some((zone) => zone.revealed);
  }
  return !fogOutside;
}

export function gridColumns(scene: TableScene): number {
  return Math.max(
    1,
    Math.ceil((scene.width - scene.grid.offset_x) / scene.grid.cell_px),
  );
}

export function tokenBox(
  token: TableToken,
  scene: TableScene,
): { left: number; top: number; width: number; height: number } {
  const cells = scene.grid.cell_px;
  const left = (scene.grid.offset_x + token.x * cells) / scene.width;
  const top = (scene.grid.offset_y + token.y * cells) / scene.height;
  return {
    left: left * 100,
    top: top * 100,
    width: ((token.w * cells) / scene.width) * 100,
    height: ((token.h * cells) / scene.height) * 100,
  };
}

export function rectPath(rect: SceneRect, grid: SceneGrid): string {
  const x = grid.offset_x + rect.x * grid.cell_px;
  const y = grid.offset_y + rect.y * grid.cell_px;
  const w = rect.w * grid.cell_px;
  const h = rect.h * grid.cell_px;
  return `M ${x} ${y} h ${w} v ${h} h ${-w} Z`;
}

export function zonePath(zone: SceneZone, grid: SceneGrid): string {
  return zone.rects.map((rect) => rectPath(rect, grid)).join(" ");
}

export function rectsPath(rects: SceneRect[], grid: SceneGrid): string {
  return rects.map((rect) => rectPath(rect, grid)).join(" ");
}

export function zoneLabelPoint(
  zone: SceneZone,
  grid: SceneGrid,
): { x: number; y: number } {
  const left = Math.min(...zone.rects.map((rect) => rect.x));
  const top = Math.min(...zone.rects.map((rect) => rect.y));
  const right = Math.max(...zone.rects.map((rect) => rect.x + rect.w));
  const bottom = Math.max(...zone.rects.map((rect) => rect.y + rect.h));
  return {
    x: grid.offset_x + ((left + right) * grid.cell_px) / 2,
    y: grid.offset_y + ((top + bottom) * grid.cell_px) / 2,
  };
}

export function mapMinWidth(scene: TableScene, cell = 32): string {
  return `${Math.ceil(gridColumns(scene) * cell)}px`;
}
