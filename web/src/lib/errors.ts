import { get, writable } from "svelte/store";

export interface ErrorEntry {
  id: number;
  code: string;
  message: string;
}

let nextId = 0;

function readString(
  error: unknown,
  key: "code" | "message",
): string | undefined {
  if (typeof error !== "object" || error === null || !(key in error)) {
    return undefined;
  }
  const value = (error as Record<string, unknown>)[key];
  return typeof value === "string" ? value : undefined;
}

export function createErrorRegion() {
  const store = writable<ErrorEntry[]>([]);
  const { subscribe, update } = store;

  return {
    subscribe,
    report(error: unknown): number {
      const code = readString(error, "code") ?? "error";
      const message = readString(error, "message") ?? "Request failed";
      const repeated = get(store).find(
        (entry) => entry.code === code && entry.message === message,
      );
      if (repeated) return repeated.id;
      const entry: ErrorEntry = { id: ++nextId, code, message };
      update((errors) => [...errors, entry]);
      return entry.id;
    },
    dismiss(id: number): void {
      update((errors) => errors.filter((error) => error.id !== id));
    },
    clear(): void {
      update(() => []);
    },
  };
}

export const errorRegion = createErrorRegion();
