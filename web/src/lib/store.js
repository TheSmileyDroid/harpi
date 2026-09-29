import { writable } from "svelte/store";

const noStatus = {
  guildId: null,
  bot: { online: false },
  connection: { connected: false, channel_id: null },
  playback: null,
};

function emptySearch() {
  return { query: "", open: false, activeIndex: 0, results: [] };
}

export function initialState() {
  return { ...noStatus, search: emptySearch() };
}

export function normalizeStatus(snapshot) {
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

export function reduceStatus(state, snapshot) {
  return { ...state, ...normalizeStatus(snapshot) };
}

export function reduceSse(state, frame) {
  if (frame?.type === "status") {
    return reduceStatus(state, frame.data);
  }
  return state;
}

export function createAppStore() {
  const { subscribe, update, set } = writable(initialState());

  return {
    subscribe,
    applyStatus(snapshot) {
      update((state) => reduceStatus(state, snapshot));
    },
    applySse(frame) {
      update((state) => reduceSse(state, frame));
    },
    setSearchQuery(query) {
      update((state) => ({ ...state, search: { ...state.search, query } }));
    },
    setSearchResults(results) {
      update((state) => ({ ...state, search: { ...state.search, results } }));
    },
    openSearch() {
      update((state) => ({
        ...state,
        search: { ...state.search, open: true },
      }));
    },
    closeSearch() {
      update((state) => ({
        ...state,
        search: { ...state.search, open: false, activeIndex: 0 },
      }));
    },
    setActiveIndex(activeIndex) {
      update((state) => ({
        ...state,
        search: { ...state.search, activeIndex },
      }));
    },
    reset() {
      set(initialState());
    },
  };
}

export const appStore = createAppStore();
