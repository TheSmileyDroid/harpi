import { afterEach, describe, expect, it, vi } from "vitest";

import type { PlaybackStatus } from "./contract/panel.gen";
import { positionSeconds, liveProgress } from "./playback-clock";
import { appStore } from "./store";

const playback: PlaybackStatus = {
  guild_id: "7",
  connected: true,
  is_playing: true,
  is_paused: false,
  current_music: {
    title: "Track",
    url: "https://example.com/track",
    uploader: "Artist",
    duration: 120,
    thumbnail: "https://example.com/thumb.jpg",
  },
  queue: [],
  layers: [],
  loop_mode: "OFF",
  volume: 1,
  progress: 10,
  channel_id: "42",
};

function status(overrides: Partial<PlaybackStatus> = {}) {
  return {
    bot: { online: true },
    guild_id: "7",
    connection: { connected: true, channel_id: "42" },
    playback: { ...playback, ...overrides },
  };
}

afterEach(() => {
  appStore.reset();
  vi.useRealTimers();
});

describe("liveProgress", () => {
  it("advances from the last sample while playing", () => {
    expect(liveProgress(10, 1000, 3500, true, null)).toBe(12.5);
  });

  it("holds the sample while paused", () => {
    expect(liveProgress(10, 1000, 3500, false, null)).toBe(10);
  });

  it("clamps at the track duration", () => {
    expect(liveProgress(119, 1000, 6000, true, 120)).toBe(120);
  });

  it("keeps advancing without a known duration", () => {
    expect(liveProgress(0, 0, 7000, true, 0)).toBe(7);
  });

  it("never moves backwards when the clocks disagree", () => {
    expect(liveProgress(10, 5000, 1000, true, null)).toBe(10);
  });
});

describe("positionSeconds", () => {
  it("advances between position frames while playing", () => {
    vi.useFakeTimers();
    appStore.applyStatus(status());

    const seen: number[] = [];
    const stop = positionSeconds.subscribe((value) => seen.push(value));
    vi.advanceTimersByTime(2000);
    stop();

    expect(seen[0]).toBeCloseTo(10, 1);
    expect(seen.at(-1)).toBeCloseTo(12, 1);
  });

  it("holds still while paused", () => {
    vi.useFakeTimers();
    appStore.applyStatus(status({ is_paused: true }));

    const seen: number[] = [];
    const stop = positionSeconds.subscribe((value) => seen.push(value));
    vi.advanceTimersByTime(2000);
    stop();

    expect(seen.at(-1)).toBeCloseTo(10, 1);
  });

  it("reports zero with no session", () => {
    let value = -1;
    const stop = positionSeconds.subscribe((next) => {
      value = next;
    });
    stop();

    expect(value).toBe(0);
  });
});
