import { ApiError } from "./api";
import { ReloadEvent, StatusSnapshot } from "./contract/panel.gen";

export const BASE_BACKOFF_MS = 1000;
export const MAX_BACKOFF_MS = 30000;

type StatusFrame = { type: "status"; data: StatusSnapshot };
type ReloadFrame = { type: "reload"; data: ReloadEvent };
export type SseFrame = StatusFrame | ReloadFrame;

const SSE_SCHEMAS = {
  status: StatusSnapshot,
  reload: ReloadEvent,
} as const;

export type SseEventName = keyof typeof SSE_SCHEMAS;

type Timer = ReturnType<typeof setTimeout>;

export function backoffDelay(
  attempt: number,
  base = BASE_BACKOFF_MS,
  max = MAX_BACKOFF_MS,
): number {
  return Math.min(base * 2 ** Math.max(0, attempt), max);
}

export function parseFrame(name: SseEventName, data: string): SseFrame | null {
  let payload: unknown;
  try {
    payload = JSON.parse(data);
  } catch {
    return null;
  }
  const result = SSE_SCHEMAS[name].safeParse(payload);
  if (!result.success) {
    return null;
  }
  return { type: name, data: result.data } as SseFrame;
}

export interface EventSourceLike {
  addEventListener(type: string, listener: (event: Event) => void): void;
  close(): void;
}

type EventSourceCtor = new (
  url: string,
  options?: { withCredentials?: boolean },
) => EventSourceLike;

export interface EventStreamOptions {
  url?: string;
  EventSourceImpl?: EventSourceCtor;
  onEvent?: (frame: SseFrame) => void;
  onError?: (error: ApiError) => void;
  onConnectionChange?: (state: string) => void;
  schedule?: (fn: () => void, timeout: number) => Timer;
  cancel?: (id: Timer) => void;
  baseDelay?: number;
  maxDelay?: number;
}

export function createEventStream({
  url = "/api/events",
  EventSourceImpl = globalThis.EventSource,
  onEvent,
  onError,
  onConnectionChange,
  schedule = setTimeout,
  cancel = clearTimeout,
  baseDelay = BASE_BACKOFF_MS,
  maxDelay = MAX_BACKOFF_MS,
}: EventStreamOptions = {}) {
  let source: EventSourceLike | null = null;
  let timer: Timer | null = null;
  let attempt = 0;
  let stopped = true;

  function dispatch(name: SseEventName, event: Event) {
    const frame = parseFrame(name, (event as MessageEvent).data);
    if (frame) {
      onEvent?.(frame);
      return;
    }
    onError?.(
      new ApiError({
        code: "contract_violation",
        message: `Unexpected ${name} event`,
        status: 0,
      }),
    );
  }

  function connect() {
    if (stopped) return;
    source = new EventSourceImpl(url, { withCredentials: true });

    source.addEventListener("open", () => {
      attempt = 0;
      onConnectionChange?.("connected");
    });

    source.addEventListener("status", (event) => dispatch("status", event));

    source.addEventListener("reload", (event) => dispatch("reload", event));

    source.addEventListener("error", () => {
      drop();
    });
  }

  function drop() {
    if (stopped) return;
    source?.close();
    source = null;
    onConnectionChange?.("reconnecting");
    const delay = backoffDelay(attempt, baseDelay, maxDelay);
    attempt += 1;
    timer = schedule(connect, delay);
  }

  return {
    start() {
      stopped = false;
      connect();
    },
    stop() {
      stopped = true;
      if (timer !== null) cancel(timer);
      timer = null;
      source?.close();
      source = null;
    },
  };
}
