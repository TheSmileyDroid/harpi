import { derived, readable } from "svelte/store";

import { appStore } from "./store";

const CLOCK_TICK_MS = 250;

const now = readable(Date.now(), (set) => {
  const timer = setInterval(() => set(Date.now()), CLOCK_TICK_MS);
  return () => clearInterval(timer);
});

export function liveProgress(
  progress: number,
  sampledAt: number,
  nowMs: number,
  playing: boolean,
  duration: number | null,
): number {
  if (!playing) return progress;
  const elapsed = Math.max(0, (nowMs - sampledAt) / 1000);
  const value = progress + elapsed;
  if (duration === null || duration <= 0) return value;
  return Math.min(value, duration);
}

export const positionSeconds = derived([appStore, now], ([$app, $now]) => {
  const playback = $app.playback;
  if (playback === null) return 0;
  const sample = $app.position;
  const playing = playback.is_playing && !playback.is_paused;
  return liveProgress(
    sample?.progress ?? playback.progress,
    sample?.at ?? $now,
    $now,
    playing,
    playback.current_music?.duration ?? null,
  );
});
