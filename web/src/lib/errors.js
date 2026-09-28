import { writable } from "svelte/store";

let nextId = 0;

export function createErrorRegion() {
  const { subscribe, update } = writable([]);

  return {
    subscribe,
    report(error) {
      const entry = {
        id: ++nextId,
        code: error?.code ?? "error",
        message: error?.message ?? "Request failed",
      };
      update((errors) => [...errors, entry]);
      return entry.id;
    },
    dismiss(id) {
      update((errors) => errors.filter((error) => error.id !== id));
    },
    clear() {
      update(() => []);
    },
  };
}

export const errorRegion = createErrorRegion();
