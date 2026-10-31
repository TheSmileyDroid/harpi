import type { z } from "zod";
import type { SheetDetail, SheetPatch } from "./contract/panel.gen";

interface AspectDraft {
  label: string;
  text: string;
}

interface StressBoxDraft {
  value: number;
  checked: boolean;
}

export interface StressTrackDraft {
  track: string;
  boxes: StressBoxDraft[];
}

interface ConsequenceDraft {
  severity: string;
  value: number;
  text: string;
}

interface ExtraDraft {
  kind: string;
  name: string;
  text: string;
  cost: number | null;
}

interface InventoryDraft {
  item: string;
  qty: number;
  note: string;
}

export interface SheetDraft {
  aspects: AspectDraft[];
  stress: StressTrackDraft[];
  consequences: ConsequenceDraft[];
  extras: ExtraDraft[];
  inventory: InventoryDraft[];
  history: string;
  notes: string;
}

export function sheetDraft(sheet: SheetDetail): SheetDraft {
  return {
    aspects: sheet.aspects.map((aspect) => ({ ...aspect })),
    stress: sheet.stress.map((track) => ({
      track: track.track,
      boxes: track.boxes.map((box) => ({ ...box })),
    })),
    consequences: sheet.consequences.map((slot) => ({
      severity: slot.severity,
      value: slot.value,
      text: slot.text,
    })),
    extras: sheet.extras.map((extra) => ({
      kind: extra.kind,
      name: extra.name,
      text: extra.text,
      cost: extra.cost,
    })),
    inventory: sheet.inventory.map((entry) => ({
      item: entry.item,
      qty: entry.qty,
      note: entry.note,
    })),
    history: sheet.history,
    notes: sheet.notes,
  };
}

export function toggleStress(
  draft: SheetDraft,
  track: string,
  value: number,
): StressTrackDraft[] {
  return draft.stress.map((candidate) =>
    candidate.track === track
      ? {
          ...candidate,
          boxes: candidate.boxes.map((box) =>
            box.value === value ? { ...box, checked: !box.checked } : box,
          ),
        }
      : candidate,
  );
}

export function wikilink(value: string): string {
  const text = value.trim();
  if (!text || text.startsWith("[[")) return text;
  return `[[${text}]]`;
}

export function patchBody(
  sheet: SheetDetail,
  draft: SheetDraft,
): z.input<typeof SheetPatch> {
  return {
    base_hash: sheet.hash,
    aspects: draft.aspects,
    stress: draft.stress,
    consequences: draft.consequences.map(({ severity, text }) => ({
      severity,
      text,
    })),
    extras: draft.extras,
    inventory: draft.inventory.map((entry) => ({
      ...entry,
      item: wikilink(entry.item),
    })),
    history: draft.history,
    notes: draft.notes,
  };
}

export function parseInteger(value: string, fallback: number): number {
  const parsed = Number.parseInt(value, 10);
  return Number.isNaN(parsed) ? fallback : parsed;
}

export function parseOptionalInteger(value: string): number | null {
  if (value.trim() === "") return null;
  const parsed = Number.parseInt(value, 10);
  return Number.isNaN(parsed) ? null : parsed;
}

export function sheetLocked(sheet: SheetDetail, conflict: boolean): boolean {
  return sheet.read_only || sheet.state !== "ok" || conflict;
}
