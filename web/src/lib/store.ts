import { writable } from "svelte/store";
import type {
  BotStatus,
  Channel,
  Connection,
  Directory,
  Guild,
  PlaybackStatus,
  Presence,
  StatusSnapshot,
  Track,
} from "./contract/panel.gen";
import type { SseFrame } from "./sse";

interface SearchState {
  query: string;
  open: boolean;
  activeIndex: number;
  results: Track[];
}

interface PositionSample {
  progress: number;
  at: number;
}

export interface AppState {
  guildId: string | null;
  bot: BotStatus;
  connection: Connection;
  playback: PlaybackStatus | null;
  position: PositionSample | null;
  presence: Presence | null;
  guilds: Guild[];
  channels: Channel[];
  pendingGuildId: string | null;
  selectedChannelId: string | null;
  search: SearchState;
  outputOpen: boolean;
}

function positionOf(playback: PlaybackStatus | null): PositionSample | null {
  return playback === null
    ? null
    : { progress: playback.progress, at: Date.now() };
}

const noStatus = {
  guildId: null,
  bot: { online: false },
  connection: { connected: false, channel_id: null },
  playback: null,
} satisfies Pick<AppState, "guildId" | "bot" | "connection" | "playback">;

function emptySearch(): SearchState {
  return { query: "", open: false, activeIndex: -1, results: [] };
}

export function initialState(): AppState {
  return {
    ...noStatus,
    position: null,
    presence: null,
    guilds: [],
    channels: [],
    pendingGuildId: null,
    selectedChannelId: null,
    search: emptySearch(),
    outputOpen: false,
  };
}

export function normalizeStatus(
  snapshot: StatusSnapshot | null | undefined,
): Pick<AppState, "guildId" | "bot" | "connection" | "playback" | "position"> {
  const playback = snapshot?.playback ?? null;
  return {
    guildId: snapshot?.guild_id ?? null,
    bot: snapshot?.bot ?? { online: false },
    connection: snapshot?.connection ?? {
      connected: false,
      channel_id: null,
    },
    playback,
    position: positionOf(playback),
  };
}

export function reduceStatus(
  state: AppState,
  snapshot: StatusSnapshot | null | undefined,
): AppState {
  return { ...state, ...normalizeStatus(snapshot) };
}

function reduceDirectory(state: AppState, directory: Directory): AppState {
  const shown = state.pendingGuildId ?? state.guildId;
  return {
    ...state,
    guilds: directory.guilds,
    channels:
      directory.guild_id === shown ? directory.channels : state.channels,
  };
}

export function reduceSse(state: AppState, frame: SseFrame): AppState {
  if (frame.type === "status") {
    return reduceStatus(state, frame.data);
  }
  if (frame.type === "presence") {
    return { ...state, presence: frame.data };
  }
  if (frame.type === "position") {
    return {
      ...state,
      position: { progress: frame.data.progress, at: Date.now() },
    };
  }
  if (frame.type === "directory") {
    return reduceDirectory(state, frame.data);
  }
  return state;
}

export function createAppStore() {
  const { subscribe, update, set } = writable<AppState>(initialState());

  return {
    subscribe,
    applyStatus(snapshot: StatusSnapshot): void {
      update((state) => reduceStatus(state, snapshot));
    },
    applySse(frame: SseFrame): void {
      update((state) => reduceSse(state, frame));
    },
    setGuilds(guilds: Guild[]): void {
      update((state) => ({ ...state, guilds }));
    },
    setChannels(channels: Channel[]): void {
      update((state) => ({ ...state, channels }));
    },
    selectGuild(pendingGuildId: string | null): void {
      update((state) => ({ ...state, pendingGuildId }));
    },
    selectChannel(selectedChannelId: string | null): void {
      update((state) => ({ ...state, selectedChannelId }));
    },
    setSearchQuery(query: string): void {
      update((state) => ({ ...state, search: { ...state.search, query } }));
    },
    setSearchResults(results: Track[]): void {
      update((state) => ({ ...state, search: { ...state.search, results } }));
    },
    openSearch(): void {
      update((state) => ({
        ...state,
        search: { ...state.search, open: true },
      }));
    },
    closeSearch(): void {
      update((state) => ({
        ...state,
        search: { ...state.search, open: false, activeIndex: -1 },
      }));
    },
    setActiveIndex(activeIndex: number): void {
      update((state) => ({
        ...state,
        search: { ...state.search, activeIndex },
      }));
    },
    openOutput(): void {
      update((state) => ({ ...state, outputOpen: true }));
    },
    closeOutput(): void {
      update((state) => ({ ...state, outputOpen: false }));
    },
    toggleOutput(): void {
      update((state) => ({ ...state, outputOpen: !state.outputOpen }));
    },
    reset(): void {
      set(initialState());
    },
  };
}

export const appStore = createAppStore();
