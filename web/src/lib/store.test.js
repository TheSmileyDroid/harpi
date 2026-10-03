import { describe, expect, it } from "vitest";
import { get } from "svelte/store";
import {
  createAppStore,
  initialState,
  normalizeStatus,
  reduceSse,
  reduceStatus,
} from "./store.js";

const snapshot = {
  bot: { online: true },
  guild_id: "7",
  connection: { connected: true, channel_id: "42" },
  playback: {
    guild_id: "7",
    connected: true,
    is_playing: true,
    is_paused: false,
    current_music: { title: "Track" },
    queue: [],
    layers: [],
    loop_mode: "OFF",
    volume: 0.7,
    progress: 0.25,
    channel_id: "42",
  },
};

describe("normalizeStatus", () => {
  it("keeps server truth for a selected guild", () => {
    expect(normalizeStatus(snapshot)).toEqual({
      guildId: "7",
      bot: { online: true },
      connection: { connected: true, channel_id: "42" },
      playback: snapshot.playback,
    });
  });

  it("falls back to an explicit no-selection shape", () => {
    expect(
      normalizeStatus({
        bot: { online: true },
        guild_id: null,
        connection: { connected: false, channel_id: null },
        playback: null,
      }),
    ).toEqual({
      guildId: null,
      bot: { online: true },
      connection: { connected: false, channel_id: null },
      playback: null,
    });
  });
});

describe("reduceStatus", () => {
  it("replaces status fields and leaves search untouched", () => {
    const before = { ...initialState(), search: { query: "abc" } };

    const after = reduceStatus(before, snapshot);

    expect(after.guildId).toBe("7");
    expect(after.playback).toBe(snapshot.playback);
    expect(after.search).toEqual({ query: "abc" });
  });
});

describe("guild selection", () => {
  it("keeps a pending client selection across status frames", () => {
    const before = { ...initialState(), pendingGuildId: "9" };

    const after = reduceStatus(before, snapshot);

    expect(after.guildId).toBe("7");
    expect(after.pendingGuildId).toBe("9");
  });
});

describe("reduceSse", () => {
  it("applies a status frame through the same reducer", () => {
    const after = reduceSse(initialState(), { type: "status", data: snapshot });

    expect(after.guildId).toBe("7");
    expect(after.bot).toEqual({ online: true });
  });

  it("ignores reload frames", () => {
    const before = initialState();

    expect(
      reduceSse(before, { type: "reload", data: { scope: "shell" } }),
    ).toBe(before);
  });
});

describe("createAppStore", () => {
  it("starts in the explicit no-selection state", () => {
    expect(get(createAppStore())).toEqual(initialState());
  });

  it("applies status snapshots from the server", () => {
    const store = createAppStore();

    store.applyStatus(snapshot);

    expect(get(store).guildId).toBe("7");
    expect(get(store).connection.channel_id).toBe("42");
  });

  it("applies SSE status frames", () => {
    const store = createAppStore();

    store.applySse({ type: "status", data: snapshot });

    expect(get(store).bot).toEqual({ online: true });
  });

  it("owns the search box state", () => {
    const store = createAppStore();

    store.setSearchQuery("queen");
    store.setSearchResults([{ title: "Bohemian Rhapsody" }]);
    store.openSearch();
    store.setActiveIndex(1);

    expect(get(store).search).toEqual({
      query: "queen",
      results: [{ title: "Bohemian Rhapsody" }],
      open: true,
      activeIndex: 1,
    });

    store.closeSearch();

    expect(get(store).search.open).toBe(false);
    expect(get(store).search.activeIndex).toBe(-1);
  });

  it("owns the guild and channel selection", () => {
    const store = createAppStore();

    store.setGuilds([{ id: "1", name: "Alpha" }]);
    store.setChannels([{ id: "10", name: "Voice" }]);
    store.selectGuild("1");
    store.selectChannel("10");

    expect(get(store).guilds).toEqual([{ id: "1", name: "Alpha" }]);
    expect(get(store).channels).toEqual([{ id: "10", name: "Voice" }]);
    expect(get(store).pendingGuildId).toBe("1");
    expect(get(store).selectedChannelId).toBe("10");
  });

  it("resets to the initial state", () => {
    const store = createAppStore();
    store.applyStatus(snapshot);

    store.reset();

    expect(get(store)).toEqual(initialState());
  });
});
