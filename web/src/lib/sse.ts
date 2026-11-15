import { ApiError } from "./api";
import {
  Directory,
  Heartbeat,
  Position,
  Presence,
  ReloadEvent,
  StatusSnapshot,
} from "./contract/panel.gen";

export const BASE_BACKOFF_MS = 1000;
export const MAX_BACKOFF_MS = 30000;
const STALL_MS = 15000;

type StatusFrame = { type: "status"; data: StatusSnapshot };
type ReloadFrame = { type: "reload"; data: ReloadEvent };
type PresenceFrame = { type: "presence"; data: Presence };
type PositionFrame = { type: "position"; data: Position };
type HeartbeatFrame = { type: "heartbeat"; data: Heartbeat };
type DirectoryFrame = { type: "directory"; data: Directory };
export type SseFrame =
  | StatusFrame
  | ReloadFrame
  | PresenceFrame
  | PositionFrame
  | HeartbeatFrame
  | DirectoryFrame;

const SSE_SCHEMAS = {
  status: StatusSnapshot,
  reload: ReloadEvent,
  presence: Presence,
  position: Position,
  heartbeat: Heartbeat,
  directory: Directory,
} as const;

export type SseEventName = keyof typeof SSE_SCHEMAS;

type Timer = ReturnType<typeof setTimeout>;

interface Schema {
  safeParse(value: unknown): { success: boolean; data?: unknown };
}

type SchemaMap = Record<string, Schema>;

export function backoffDelay(
  attempt: number,
  base = BASE_BACKOFF_MS,
  max = MAX_BACKOFF_MS,
): number {
  return Math.min(base * 2 ** Math.max(0, attempt), max);
}

function parseFrameWith<F>(
  schemas: SchemaMap,
  wrap: (name: string, data: unknown) => F,
  name: string,
  data: string,
): F | null {
  const schema = schemas[name];
  if (!schema) return null;
  let payload: unknown;
  try {
    payload = JSON.parse(data);
  } catch {
    return null;
  }
  const result = schema.safeParse(payload);
  return result.success ? wrap(name, result.data) : null;
}

function parserFor<F>(
  schemas: SchemaMap,
  wrap: (name: string, data: unknown) => F,
): (name: string, data: string) => F | null {
  return (name, data) => parseFrameWith(schemas, wrap, name, data);
}

export function parseFrame(name: SseEventName, data: string): SseFrame | null {
  return parseFrameWith(
    SSE_SCHEMAS,
    (event, payload) => ({ type: event, data: payload }) as SseFrame,
    name,
    data,
  );
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
  stallAfter?: number;
}

interface StreamOptions<F> extends Omit<EventStreamOptions, "onEvent"> {
  schemas: SchemaMap;
  parse: (name: string, data: string) => F | null;
  onEvent?: (frame: F) => void;
}

function createStream<F>({
  url = "/api/events",
  schemas,
  parse,
  EventSourceImpl = globalThis.EventSource,
  onEvent,
  onError,
  onConnectionChange,
  schedule = setTimeout,
  cancel = clearTimeout,
  baseDelay = BASE_BACKOFF_MS,
  maxDelay = MAX_BACKOFF_MS,
  stallAfter = STALL_MS,
}: StreamOptions<F>) {
  let source: EventSourceLike | null = null;
  let timer: Timer | null = null;
  let watchdog: Timer | null = null;
  let attempt = 0;
  let stopped = true;

  const names = Object.keys(schemas);

  function armWatchdog() {
    if (watchdog !== null) cancel(watchdog);
    watchdog = schedule(() => {
      watchdog = null;
      drop();
    }, stallAfter);
  }

  function clearWatchdog() {
    if (watchdog === null) return;
    cancel(watchdog);
    watchdog = null;
  }

  function clearTimer() {
    if (timer === null) return;
    cancel(timer);
    timer = null;
  }

  function dispatch(name: string, event: Event) {
    const frame = parse(name, (event as MessageEvent).data);
    if (frame) {
      armWatchdog();
      onEvent?.(frame);
      return;
    }
    onError?.(
      new ApiError({
        code: "contract_violation",
        message: `Evento inesperado: ${name}`,
        status: 0,
      }),
    );
  }

  function connect() {
    if (stopped) return;
    source = new EventSourceImpl(url, { withCredentials: true });
    armWatchdog();

    source.addEventListener("open", () => {
      attempt = 0;
      onConnectionChange?.("connected");
    });

    for (const name of names) {
      source.addEventListener(name, (event) => dispatch(name, event));
    }

    source.addEventListener("error", () => {
      drop();
    });
  }

  function drop() {
    if (stopped) return;
    clearWatchdog();
    source?.close();
    source = null;
    onConnectionChange?.("reconnecting");
    const delay = backoffDelay(attempt, baseDelay, maxDelay);
    attempt += 1;
    timer = schedule(connect, delay);
  }

  function forceReconnect() {
    if (stopped) return;
    clearTimer();
    clearWatchdog();
    source?.close();
    source = null;
    attempt = 0;
    connect();
  }

  function reconnect() {
    if (stopped) return;
    clearTimer();
    drop();
  }

  return {
    start() {
      if (!stopped) return;
      stopped = false;
      connect();
    },
    stop() {
      stopped = true;
      clearTimer();
      clearWatchdog();
      source?.close();
      source = null;
    },
    forceReconnect,
    reconnect,
  };
}

export function createEventStream(options: EventStreamOptions = {}) {
  return createStream<SseFrame>({
    ...options,
    schemas: SSE_SCHEMAS,
    parse: parserFor(
      SSE_SCHEMAS,
      (name, payload) => ({ type: name, data: payload }) as SseFrame,
    ),
  });
}
