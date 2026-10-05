import { writable } from "svelte/store";
import type {
  BotStatus,
  Channel,
  Connection,
  Guild,
  PlaybackStatus,
  SseFrame,
  StatusSnapshot,
  Track,
} from "./types";

interface SearchState {
  query: string;
  open: boolean;
  activeIndex: number;
  results: Track[];
}

export interface AppState {
  guildId: string | null;
  bot: BotStatus;
  connection: Connection;
  playback: PlaybackStatus | null;
  guilds: Guild[];
  channels: Channel[];
  pendingGuildId: string | null;
  selectedChannelId: string | null;
  search: SearchState;
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
    guilds: [],
    channels: [],
    pendingGuildId: null,
    selectedChannelId: null,
    search: emptySearch(),
  };
}

export function normalizeStatus(
  snapshot: StatusSnapshot | null | undefined,
): Pick<AppState, "guildId" | "bot" | "connection" | "playback"> {
  return {
    guildId: snapshot?.guild_id ?? null,
    bot: snapshot?.bot ?? { online: false },
    connection: snapshot?.connection ?? {
      connected: false,
      channel_id: null,
    },
    playback: snapshot?.playback ?? null,
  };
}

export function reduceStatus(
  state: AppState,
  snapshot: StatusSnapshot | null | undefined,
): AppState {
  return { ...state, ...normalizeStatus(snapshot) };
}

export function reduceSse(state: AppState, frame: SseFrame): AppState {
  if (frame.type === "status") {
    return reduceStatus(state, frame.data);
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
    reset(): void {
      set(initialState());
    },
  };
}

export const appStore = createAppStore();
