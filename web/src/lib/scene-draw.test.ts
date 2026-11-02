import { describe, expect, it } from "vitest";
import {
  addRoom,
  canDraw,
  cellFromPoint,
  clampCell,
  eraseCells,
  gridBounds,
  normalizeRects,
  outlinePath,
  zonesFit,
} from "./scene-draw";
import type { SceneGrid, SceneRect, SceneZone } from "./contract/panel.gen";

const GRID: SceneGrid = {
  cell_px: 70,
  offset_x: 10,
  offset_y: 20,
  visible: true,
};

const UNION_ROWS: SceneRect[] = [
  { x: 0, y: 0, w: 2, h: 1 },
  { x: 0, y: 1, w: 3, h: 1 },
  { x: 1, y: 2, w: 2, h: 1 },
];

function room(
  id: string,
  label: string,
  rects: SceneRect[],
  revealed = false,
): SceneZone {
  return { id, label, revealed, rects };
}

describe("scene drawing geometry", () => {
  it("maps a point to the cell under it", () => {
    expect(cellFromPoint(10, 20, GRID)).toEqual({ x: 0, y: 0 });
    expect(cellFromPoint(79, 89, GRID)).toEqual({ x: 0, y: 0 });
    expect(cellFromPoint(80, 90, GRID)).toEqual({ x: 1, y: 1 });
  });

  it("clamps a cell inside the map", () => {
    const bounds = gridBounds(240, 160, GRID);

    expect(bounds).toEqual({ columns: 4, rows: 2 });
    expect(clampCell({ x: -3, y: 9 }, bounds)).toEqual({ x: 0, y: 1 });
  });

  it("refuses to draw when the offset leaves no columns or rows", () => {
    expect(canDraw(gridBounds(100, 100, { ...GRID, offset_x: 101 }))).toBe(
      false,
    );
    expect(canDraw(gridBounds(100, 100, { ...GRID, offset_y: 151 }))).toBe(
      false,
    );
    expect(canDraw(gridBounds(100, 100, GRID))).toBe(true);
  });

  it("creates a room from a dragged rectangle", () => {
    const zones = addRoom([], { x: 1, y: 1, w: 2, h: 2 }, "Sala 1");

    expect(zones).toEqual([
      {
        id: "zon_1",
        label: "Sala 1",
        revealed: false,
        rects: [{ x: 1, y: 1, w: 2, h: 2 }],
      },
    ]);
  });

  it("merges a partially overlapping rectangle into the same room", () => {
    const zones = addRoom(
      [room("zon_a", "Sala", [{ x: 0, y: 0, w: 2, h: 2 }])],
      { x: 1, y: 1, w: 2, h: 2 },
      "Sala 2",
    );

    expect(zones).toHaveLength(1);
    expect(zones[0]?.id).toBe("zon_a");
    expect(zones[0]?.label).toBe("Sala");
    expect(zones[0]?.rects).toEqual(UNION_ROWS);
  });

  it("keeps a touching rectangle as another room", () => {
    const zones = addRoom(
      [room("zon_a", "Sala", [{ x: 0, y: 0, w: 2, h: 2 }])],
      { x: 2, y: 0, w: 1, h: 2 },
      "Sala 2",
    );

    expect(zones.map((zone) => zone.id)).toEqual(["zon_a", "zon_1"]);
    expect(zones[1]?.rects).toEqual([{ x: 2, y: 0, w: 1, h: 2 }]);
  });

  it("joins two rooms when the new rectangle overlaps both", () => {
    const zones = addRoom(
      [
        room("zon_a", "A", [{ x: 0, y: 0, w: 1, h: 1 }], true),
        room("zon_b", "B", [{ x: 2, y: 0, w: 1, h: 1 }]),
      ],
      { x: 0, y: 0, w: 3, h: 1 },
      "Sala 3",
    );

    expect(zones).toHaveLength(1);
    expect(zones[0]?.id).toBe("zon_a");
    expect(zones[0]?.revealed).toBe(true);
    expect(zones[0]?.rects).toEqual([{ x: 0, y: 0, w: 3, h: 1 }]);
  });

  it("cuts only the touched cells and splits the same room", () => {
    const zones = eraseCells(
      [room("zon_a", "Sala", [{ x: 0, y: 0, w: 3, h: 1 }])],
      [{ x: 1, y: 0 }],
    );

    expect(zones).toHaveLength(1);
    expect(zones[0]?.id).toBe("zon_a");
    expect(zones[0]?.rects).toEqual([
      { x: 0, y: 0, w: 1, h: 1 },
      { x: 2, y: 0, w: 1, h: 1 },
    ]);
  });

  it("drops a room whose every cell was erased", () => {
    const zones = eraseCells(
      [room("zon_a", "Sala", [{ x: 0, y: 0, w: 1, h: 1 }])],
      [{ x: 0, y: 0 }],
    );

    expect(zones).toEqual([]);
  });

  it("normalizes overlapping input into non-overlapping rectangles", () => {
    const rects = normalizeRects([
      { x: 0, y: 0, w: 2, h: 2 },
      { x: 1, y: 1, w: 2, h: 2 },
    ]);

    expect(rects).toEqual(UNION_ROWS);
  });

  it("traces the outline without an internal line", () => {
    const path = outlinePath(
      room("zon_l", "Sala em L", [
        { x: 0, y: 0, w: 2, h: 1 },
        { x: 0, y: 1, w: 1, h: 1 },
      ]),
      { ...GRID, offset_x: 0, offset_y: 0 },
    );

    expect(path).toBe("M 0 0 L 140 0 L 140 70 L 70 70 L 70 140 L 0 140 Z");
  });

  it("detects a room that leaves the map", () => {
    const bounds = { columns: 4, rows: 2 };

    expect(
      zonesFit([room("zon_a", "Sala", [{ x: 0, y: 0, w: 4, h: 2 }])], bounds),
    ).toBe(true);
    expect(
      zonesFit([room("zon_a", "Sala", [{ x: 3, y: 0, w: 2, h: 1 }])], bounds),
    ).toBe(false);
  });
});
