import { writable } from "svelte/store";

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
  const { subscribe, update } = writable<ErrorEntry[]>([]);

  return {
    subscribe,
    report(error: unknown): number {
      const entry: ErrorEntry = {
        id: ++nextId,
        code: readString(error, "code") ?? "error",
        message: readString(error, "message") ?? "Request failed",
      };
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
