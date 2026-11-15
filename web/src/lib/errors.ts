import { get, writable } from "svelte/store";

export interface ErrorEntry {
  id: number;
  code: string;
  message: string;
  key: string;
}

let nextId = 0;

const MESSAGES_BY_CODE: Record<string, string> = {
  bad_request: "Requisição inválida.",
  forbidden: "Sem permissão.",
  not_found: "Não encontrado.",
  payload_too_large: "O conteúdo enviado é grande demais.",
  too_many_requests: "Muitas requisições — espere um pouco.",
};

function messageFor(error: unknown, code: string): string {
  const known = MESSAGES_BY_CODE[code];
  if (known) return known;
  return readString(error, "message") ?? "A requisição falhou";
}

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
      const raw = readString(error, "message") ?? "";
      const message = messageFor(error, code);
      const repeated = get(store).find(
        (entry) => entry.code === code && entry.key === raw,
      );
      if (repeated) return repeated.id;
      const entry: ErrorEntry = { id: ++nextId, code, message, key: raw };
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
