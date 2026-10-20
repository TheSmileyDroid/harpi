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
  stallAfter?: number;
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
  stallAfter = STALL_MS,
}: EventStreamOptions = {}) {
  let source: EventSourceLike | null = null;
  let timer: Timer | null = null;
  let watchdog: Timer | null = null;
  let attempt = 0;
  let stopped = true;

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

  function dispatch(name: SseEventName, event: Event) {
    const frame = parseFrame(name, (event as MessageEvent).data);
    if (frame) {
      armWatchdog();
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
    armWatchdog();

    source.addEventListener("open", () => {
      attempt = 0;
      onConnectionChange?.("connected");
    });

    for (const name of Object.keys(SSE_SCHEMAS) as SseEventName[]) {
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

  return {
    start() {
      stopped = false;
      connect();
    },
    stop() {
      stopped = true;
      if (timer !== null) cancel(timer);
      timer = null;
      clearWatchdog();
      source?.close();
      source = null;
    },
  };
}
