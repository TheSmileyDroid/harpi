import { get, writable } from "svelte/store";
import { ApiError } from "./api";

export interface ErrorEntry {
  id: number;
  code: string;
  message: string;
  key: string;
}

export function codeNote(
  error: unknown,
  messages: Record<string, string>,
  fallback: string,
): string {
  if (error instanceof ApiError) {
    const message = messages[error.code];
    if (message) return message;
  }
  return fallback;
}

let nextId = 0;

const MESSAGES_BY_CODE: Record<string, string> = {
  bad_request: "Requisição inválida.",
  forbidden: "Sem permissão.",
  invalid_decision: "A decisão é inválida.",
  invalid_payload: "Confira os dados enviados.",
  invalid_sheet: "A ficha é inválida.",
  not_found: "Não encontrado.",
  payload_too_large: "O conteúdo enviado é grande demais.",
  quota_exceeded: "A cota de armazenamento acabou.",
  sheet_conflict: "A ficha mudou no disco.",
  sheet_invalid: "A ficha é inválida.",
  sheet_missing: "O arquivo da ficha não está no vault.",
  sheet_present: "O arquivo da ficha já está no vault.",
  sheet_read_only: "A ficha está somente leitura.",
  storage_unavailable: "O armazenamento está indisponível.",
  table_closed: "A mesa está fechada.",
  too_many_requests: "Muitas requisições — espere um pouco.",
  vault_unavailable: "O vault está indisponível.",
  vault_write_failed: "Não foi possível gravar no vault.",
};

export function codeMessage(error: unknown): string | null {
  const code = readString(error, "code");
  if (!code) return null;
  return MESSAGES_BY_CODE[code] ?? null;
}

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
