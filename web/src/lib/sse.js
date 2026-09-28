export const BASE_BACKOFF_MS = 1000;
export const MAX_BACKOFF_MS = 30000;

export function backoffDelay(
  attempt,
  base = BASE_BACKOFF_MS,
  max = MAX_BACKOFF_MS,
) {
  return Math.min(base * 2 ** Math.max(0, attempt), max);
}

export function parseFrame(type, data) {
  try {
    return { type, data: JSON.parse(data) };
  } catch {
    return null;
  }
}

export function createEventStream({
  url = "/api/events",
  EventSourceImpl = globalThis.EventSource,
  onEvent,
  onConnectionChange,
  schedule = setTimeout,
  cancel = clearTimeout,
  baseDelay = BASE_BACKOFF_MS,
  maxDelay = MAX_BACKOFF_MS,
} = {}) {
  let source = null;
  let timer = null;
  let attempt = 0;
  let stopped = true;

  function connect() {
    if (stopped) return;
    source = new EventSourceImpl(url, { withCredentials: true });

    source.addEventListener("open", () => {
      attempt = 0;
      onConnectionChange?.("connected");
    });

    source.addEventListener("status", (event) => {
      const frame = parseFrame("status", event.data);
      if (frame) onEvent?.(frame);
    });

    source.addEventListener("reload", (event) => {
      const frame = parseFrame("reload", event.data);
      if (frame) onEvent?.(frame);
    });

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
