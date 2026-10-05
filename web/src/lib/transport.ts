const LOOP_CYCLE: Record<string, string> = {
  OFF: "track",
  TRACK: "queue",
  QUEUE: "off",
};

function clamp(value: number, min: number, max: number): number {
  return Math.min(Math.max(value, min), max);
}

export function pointerRatio(offsetX: number, width: number): number {
  if (!Number.isFinite(width) || width <= 0) return 0;
  if (!Number.isFinite(offsetX)) return 0;
  return clamp(offsetX / width, 0, 1);
}

export function seekTarget(ratio: number, duration: number): number {
  if (!Number.isFinite(duration) || duration <= 0) return 0;
  if (!Number.isFinite(ratio)) return 0;
  return clamp(ratio, 0, 1) * duration;
}

export function seekDisplayRatio(
  seeking: boolean,
  seekRatio: number,
  serverRatio: number,
): number {
  const ratio = seeking ? seekRatio : serverRatio;
  if (!Number.isFinite(ratio)) return 0;
  return clamp(ratio, 0, 1);
}

export function volumeGain(position: number): number {
  if (!Number.isFinite(position)) return 0;
  return clamp(position, 0, 1) ** 2;
}

export function volumePosition(gain: number): number {
  if (!Number.isFinite(gain)) return 0;
  return Math.sqrt(clamp(gain, 0, 1));
}

export function nextLoopMode(mode: string | null | undefined): string {
  return (mode ? LOOP_CYCLE[mode] : undefined) ?? "off";
}
