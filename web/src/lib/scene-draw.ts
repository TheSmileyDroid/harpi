import type { SceneGrid, SceneRect, SceneZone } from "./contract/panel.gen";

export interface Cell {
  x: number;
  y: number;
}

export interface GridBounds {
  columns: number;
  rows: number;
}

export function gridBounds(
  width: number,
  height: number,
  grid: SceneGrid,
): GridBounds {
  return {
    columns: Math.max(0, Math.ceil((width - grid.offset_x) / grid.cell_px)),
    rows: Math.max(0, Math.ceil((height - grid.offset_y) / grid.cell_px)),
  };
}

export function canDraw(bounds: GridBounds): boolean {
  return bounds.columns > 0 && bounds.rows > 0;
}

export function cellFromPoint(x: number, y: number, grid: SceneGrid): Cell {
  return {
    x: Math.floor((x - grid.offset_x) / grid.cell_px),
    y: Math.floor((y - grid.offset_y) / grid.cell_px),
  };
}

export function clampCell(cell: Cell, bounds: GridBounds): Cell {
  return {
    x: Math.min(Math.max(cell.x, 0), Math.max(bounds.columns - 1, 0)),
    y: Math.min(Math.max(cell.y, 0), Math.max(bounds.rows - 1, 0)),
  };
}

export function cellRect(start: Cell, end: Cell): SceneRect {
  const x = Math.min(start.x, end.x);
  const y = Math.min(start.y, end.y);
  return {
    x,
    y,
    w: Math.abs(end.x - start.x) + 1,
    h: Math.abs(end.y - start.y) + 1,
  };
}

function overlap(a: SceneRect, b: SceneRect): boolean {
  return (
    a.x < b.x + b.w && a.x + a.w > b.x && a.y < b.y + b.h && a.y + a.h > b.y
  );
}

export function normalizeRects(rects: SceneRect[]): SceneRect[] {
  const xs = uniqueSorted(rects.flatMap((rect) => [rect.x, rect.x + rect.w]));
  const ys = uniqueSorted(rects.flatMap((rect) => [rect.y, rect.y + rect.h]));
  if (xs.length < 2 || ys.length < 2) return [];
  const result: SceneRect[] = [];
  let active = new Map<string, SceneRect>();
  for (let row = 0; row < ys.length - 1; row += 1) {
    const runs = coveredRuns(xs, ys, row, rects);
    const next = new Map<string, SceneRect>();
    for (const run of runs) {
      const left = xs[run[0]] ?? 0;
      const right = xs[run[1] + 1] ?? 0;
      const top = ys[row] ?? 0;
      const key = `${left}:${right}`;
      const previous = active.get(key);
      const height = (ys[row + 1] ?? top) - top;
      if (previous) {
        previous.h += height;
        next.set(key, previous);
      } else {
        const rect = { x: left, y: top, w: right - left, h: height };
        result.push(rect);
        next.set(key, rect);
      }
    }
    active = next;
  }
  return result;
}

function uniqueSorted(values: number[]): number[] {
  return [...new Set(values)].sort((a, b) => a - b);
}

function coveredRuns(
  xs: number[],
  ys: number[],
  row: number,
  rects: SceneRect[],
): Array<[number, number]> {
  const runs: Array<[number, number]> = [];
  let start: number | null = null;
  for (let column = 0; column < xs.length - 1; column += 1) {
    const left = xs[column] ?? 0;
    const right = xs[column + 1] ?? 0;
    const top = ys[row] ?? 0;
    const bottom = ys[row + 1] ?? 0;
    const covered = rects.some(
      (rect) =>
        rect.x <= left &&
        right <= rect.x + rect.w &&
        rect.y <= top &&
        bottom <= rect.y + rect.h,
    );
    if (covered && start === null) start = column;
    if (!covered && start !== null) {
      runs.push([start, column - 1]);
      start = null;
    }
  }
  if (start !== null) runs.push([start, xs.length - 2]);
  return runs;
}

export function addRoom(
  zones: SceneZone[],
  rect: SceneRect,
  label: string,
): SceneZone[] {
  const touched = zones.filter((zone) =>
    zone.rects.some((item) => overlap(item, rect)),
  );
  if (touched.length === 0) {
    const zone: SceneZone = {
      id: nextZoneId(zones),
      label,
      revealed: false,
      rects: normalizeRects([rect]),
    };
    return [...zones, zone];
  }
  const primary = touched[0];
  if (!primary) return zones;
  const merged: SceneZone = {
    ...primary,
    rects: normalizeRects([...touched.flatMap((zone) => zone.rects), rect]),
  };
  return zones.flatMap((zone) => {
    if (zone.id === primary.id) return [merged];
    if (touched.includes(zone)) return [];
    return [zone];
  });
}

function nextZoneId(zones: SceneZone[]): string {
  return nextAvailable(
    zones.map((zone) => zone.id),
    (index) => `zon_${index}`,
  );
}

export function nextRoomLabel(zones: SceneZone[]): string {
  return nextAvailable(
    zones.map((zone) => zone.label),
    (index) => `Sala ${index}`,
  );
}

function nextAvailable(
  used: string[],
  format: (index: number) => string,
): string {
  const taken = new Set(used);
  let index = 1;
  while (taken.has(format(index))) index += 1;
  return format(index);
}

export function eraseCells(zones: SceneZone[], cells: Cell[]): SceneZone[] {
  if (cells.length === 0) return zones;
  return zones
    .map((zone) => {
      let rects = zone.rects;
      for (const cell of cells) {
        rects = rects.flatMap((rect) =>
          subtractRect(rect, { x: cell.x, y: cell.y, w: 1, h: 1 }),
        );
      }
      return { ...zone, rects: normalizeRects(rects) };
    })
    .filter((zone) => zone.rects.length > 0);
}

function subtractRect(rect: SceneRect, cut: SceneRect): SceneRect[] {
  if (!overlap(rect, cut)) return [rect];
  const parts: SceneRect[] = [];
  const right = rect.x + rect.w;
  const bottom = rect.y + rect.h;
  if (cut.y > rect.y) {
    parts.push({ x: rect.x, y: rect.y, w: rect.w, h: cut.y - rect.y });
  }
  if (cut.y + cut.h < bottom) {
    parts.push({
      x: rect.x,
      y: cut.y + cut.h,
      w: rect.w,
      h: bottom - (cut.y + cut.h),
    });
  }
  const top = Math.max(rect.y, cut.y);
  const low = Math.min(bottom, cut.y + cut.h);
  if (cut.x > rect.x) {
    parts.push({ x: rect.x, y: top, w: cut.x - rect.x, h: low - top });
  }
  if (cut.x + cut.w < right) {
    parts.push({
      x: cut.x + cut.w,
      y: top,
      w: right - (cut.x + cut.w),
      h: low - top,
    });
  }
  return parts.filter((part) => part.w > 0 && part.h > 0);
}

export function zonesFit(zones: SceneZone[], bounds: GridBounds): boolean {
  return zones.every((zone) =>
    zone.rects.every(
      (rect) =>
        rect.x >= 0 &&
        rect.y >= 0 &&
        rect.x + rect.w <= bounds.columns &&
        rect.y + rect.h <= bounds.rows,
    ),
  );
}

export function eraseLine(start: Cell, end: Cell): Cell[] {
  const cells: Cell[] = [];
  let x = start.x;
  let y = start.y;
  const dx = Math.abs(end.x - start.x);
  const dy = Math.abs(end.y - start.y);
  const stepX = start.x < end.x ? 1 : -1;
  const stepY = start.y < end.y ? 1 : -1;
  let error = dx - dy;
  while (true) {
    cells.push({ x, y });
    if (x === end.x && y === end.y) break;
    const doubled = error * 2;
    if (doubled > -dy) {
      error -= dy;
      x += stepX;
    }
    if (doubled < dx) {
      error += dx;
      y += stepY;
    }
  }
  return cells;
}

export function outlinePath(zone: SceneZone, grid: SceneGrid): string {
  return traceLoops(zone.rects)
    .map((loop) => loopPath(loop, grid))
    .join(" ");
}

function traceLoops(rects: SceneRect[]): Array<Array<[number, number]>> {
  const xs = uniqueSorted(rects.flatMap((rect) => [rect.x, rect.x + rect.w]));
  const ys = uniqueSorted(rects.flatMap((rect) => [rect.y, rect.y + rect.h]));
  if (xs.length < 2 || ys.length < 2) return [];
  const edges = new Set<string>();
  const starts = new Map<string, Array<[number, number]>>();
  for (let row = 0; row < ys.length - 1; row += 1) {
    for (const run of coveredRuns(xs, ys, row, rects)) {
      const first = run[0] ?? 0;
      const last = run[1] ?? first;
      for (let column = first; column <= last; column += 1) {
        addCellEdges(
          edges,
          xs[column] ?? 0,
          ys[row] ?? 0,
          xs[column + 1] ?? 0,
          ys[row + 1] ?? 0,
        );
      }
    }
  }
  const boundary: Array<[[number, number], [number, number]]> = [];
  for (const edge of edges) {
    const [from, to] = parseEdge(edge);
    const reverse = edgeKey(to, from);
    if (edges.has(reverse)) continue;
    boundary.push([from, to]);
  }
  for (const [from, to] of boundary) {
    const key = pointKey(from);
    const list = starts.get(key) ?? [];
    list.push(to);
    starts.set(key, list);
  }
  const loops: Array<Array<[number, number]>> = [];
  const points = [...starts.keys()].sort(comparePointKeys);
  for (const key of points) {
    while ((starts.get(key) ?? []).length > 0) {
      loops.push(walkLoop(key, starts));
    }
  }
  return loops;
}

function addCellEdges(
  edges: Set<string>,
  left: number,
  top: number,
  right: number,
  bottom: number,
): void {
  edges.add(edgeKey([left, top], [right, top]));
  edges.add(edgeKey([right, top], [right, bottom]));
  edges.add(edgeKey([right, bottom], [left, bottom]));
  edges.add(edgeKey([left, bottom], [left, top]));
}

function edgeKey(from: [number, number], to: [number, number]): string {
  return `${pointKey(from)}>${pointKey(to)}`;
}

function pointKey([x, y]: [number, number]): string {
  return `${x},${y}`;
}

function parseEdge(edge: string): [[number, number], [number, number]] {
  const [from = "", to = ""] = edge.split(">");
  return [parsePoint(from), parsePoint(to)];
}

function parsePoint(point: string): [number, number] {
  const [x = "0", y = "0"] = point.split(",");
  return [Number(x), Number(y)];
}

function comparePointKeys(a: string, b: string): number {
  const [ax, ay] = parsePoint(a);
  const [bx, by] = parsePoint(b);
  return ay - by || ax - bx;
}

function walkLoop(
  startKey: string,
  starts: Map<string, Array<[number, number]>>,
): Array<[number, number]> {
  const start = parsePoint(startKey);
  const loop: Array<[number, number]> = [start];
  let current = start;
  while (true) {
    const key = pointKey(current);
    const ends = starts.get(key);
    if (!ends || ends.length === 0) break;
    const following = ends.shift() as [number, number];
    if (ends.length === 0) starts.delete(key);
    loop.push(following);
    current = following;
    if (current[0] === start[0] && current[1] === start[1]) break;
  }
  return simplify(loop);
}

function simplify(loop: Array<[number, number]>): Array<[number, number]> {
  const first = loop[0];
  const last = loop[loop.length - 1];
  const points =
    first && last && first[0] === last[0] && first[1] === last[1]
      ? loop.slice(0, -1)
      : loop;
  if (points.length < 3) return points;
  const kept = points.filter((point, index) => {
    const before = points[(index - 1 + points.length) % points.length] ?? point;
    const after = points[(index + 1) % points.length] ?? point;
    return !collinear(before, point, after);
  });
  return kept;
}

function collinear(
  before: [number, number],
  point: [number, number],
  after: [number, number],
): boolean {
  return (
    (point[0] - before[0]) * (after[1] - point[1]) ===
    (point[1] - before[1]) * (after[0] - point[0])
  );
}

function loopPath(loop: Array<[number, number]>, grid: SceneGrid): string {
  const points = loop.map(
    ([x, y]) =>
      [x * grid.cell_px + grid.offset_x, y * grid.cell_px + grid.offset_y] as [
        number,
        number,
      ],
  );
  const [head, ...rest] = points;
  if (!head) return "";
  return [
    `M ${head[0]} ${head[1]}`,
    ...rest.map(([x, y]) => `L ${x} ${y}`),
    "Z",
  ].join(" ");
}
