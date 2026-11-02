import { ApiError } from "./api";

const MOVE_INTERVAL_MS = 100;
const MOVE_HEARTBEAT_MS = 5000;
const MOVE_LIMITED_INTERVAL_MS = 1000;
export const MOVE_LIMIT_MS = 30000;

interface MoveTarget {
  token_id: string;
  x: number;
  y: number;
}

export interface MoveBatch {
  drag_id: string;
  final: boolean;
  moves: MoveTarget[];
}

type Timer = ReturnType<typeof setTimeout>;
type Schedule = (fn: () => void, ms: number) => Timer;
type Cancel = (id: Timer) => void;

export interface MovePumpOptions {
  send: (batch: MoveBatch) => Promise<unknown>;
  schedule?: Schedule;
  cancel?: Cancel;
  now?: () => number;
  onLimited?: (limited: boolean) => void;
  onEnd?: () => void;
}

interface DragState {
  id: string;
  target: MoveTarget;
  sent: MoveTarget | null;
  lastSentAt: number | null;
}

interface PendingBegin {
  tokenId: string;
  x: number;
  y: number;
  final: boolean;
}

function sameTarget(
  left: MoveTarget | null,
  right: MoveTarget | null,
): boolean {
  return (
    left !== null &&
    right !== null &&
    left.token_id === right.token_id &&
    left.x === right.x &&
    left.y === right.y
  );
}

export function createMovePump(options: MovePumpOptions) {
  const schedule: Schedule =
    options.schedule ?? ((fn, ms) => setTimeout(fn, ms));
  const cancel: Cancel = options.cancel ?? ((id) => clearTimeout(id));
  const now = options.now ?? (() => Date.now());
  let drag: DragState | null = null;
  let pendingBegin: PendingBegin | null = null;
  let finishing = false;
  let inFlight = false;
  let limitedUntil = 0;
  let tickTimer: Timer | null = null;
  let beatTimer: Timer | null = null;
  let limitTimer: Timer | null = null;
  let sequence = 0;

  function interval(): number {
    return now() < limitedUntil ? MOVE_LIMITED_INTERVAL_MS : MOVE_INTERVAL_MS;
  }

  function dueAt(state: DragState): number {
    return state.lastSentAt === null ? now() : state.lastSentAt + interval();
  }

  function clearTick(): void {
    if (tickTimer !== null) {
      cancel(tickTimer);
      tickTimer = null;
    }
  }

  function clearBeat(): void {
    if (beatTimer !== null) {
      cancel(beatTimer);
      beatTimer = null;
    }
  }

  function armTick(): void {
    clearTick();
    if (drag === null) return;
    if (!finishing && sameTarget(drag.target, drag.sent)) return;
    const delay = Math.max(0, dueAt(drag) - now());
    tickTimer = schedule(runTick, delay);
  }

  function armBeat(): void {
    if (beatTimer !== null) return;
    beatTimer = schedule(runBeat, MOVE_HEARTBEAT_MS);
  }

  function noteLimit(): void {
    if (limitedUntil === 0 || now() < limitedUntil) return;
    limitedUntil = 0;
    options.onLimited?.(false);
  }

  function stop(): void {
    clearTick();
    clearBeat();
    drag = null;
    finishing = false;
    noteLimit();
    if (limitedUntil === 0 && limitTimer !== null) {
      cancel(limitTimer);
      limitTimer = null;
    }
    options.onEnd?.();
  }

  function start(tokenId: string, x: number, y: number): void {
    sequence += 1;
    drag = {
      id: `drag_${sequence}_${Math.trunc(now()).toString(36)}`,
      target: { token_id: tokenId, x, y },
      sent: null,
      lastSentAt: limitedUntil > now() ? now() : null,
    };
    finishing = false;
    armBeat();
    armTick();
  }

  function resumePending(): void {
    if (pendingBegin === null) return;
    const next = pendingBegin;
    pendingBegin = null;
    start(next.tokenId, next.x, next.y);
    if (!next.final) return;
    finishing = true;
    clearTick();
    clearBeat();
    void dispatch(true);
  }

  async function runTick(): Promise<void> {
    tickTimer = null;
    if (drag === null || inFlight) return;
    if (now() < dueAt(drag)) {
      armTick();
      return;
    }
    await dispatch(finishing);
  }

  async function runBeat(): Promise<void> {
    beatTimer = null;
    if (drag === null) return;
    if (!inFlight && !finishing) await dispatch(false, true);
    armBeat();
  }

  function limit(error: unknown): void {
    if (!(error instanceof ApiError) || error.status !== 429) return;
    limitedUntil = now() + MOVE_LIMIT_MS;
    options.onLimited?.(true);
    clearTick();
    if (limitTimer !== null) cancel(limitTimer);
    limitTimer = schedule(release, MOVE_LIMIT_MS);
  }

  function release(): void {
    limitTimer = null;
    limitedUntil = 0;
    options.onLimited?.(false);
    armTick();
  }

  function refused(error: unknown): boolean {
    return (
      error instanceof ApiError && [403, 404, 409, 422].includes(error.status)
    );
  }

  async function sendNow(
    final: boolean,
    state: DragState,
  ): Promise<unknown | null> {
    const target = { ...state.target };
    try {
      await options.send({
        drag_id: state.id,
        final,
        moves: [{ ...target }],
      });
      state.sent = target;
      return null;
    } catch (error) {
      limit(error);
      return error;
    }
  }

  async function dispatch(final: boolean, force = false): Promise<void> {
    if (drag === null || inFlight) return;
    const state = drag;
    if (!final && !force && sameTarget(state.target, state.sent)) return;
    inFlight = true;
    state.lastSentAt = now();
    let failure: unknown = null;
    try {
      failure = await sendNow(final, state);
    } finally {
      inFlight = false;
    }
    if (drag === null) return;
    if (final && failure === null) {
      stop();
      resumePending();
      return;
    }
    if (refused(failure)) {
      stop();
      resumePending();
      return;
    }
    armTick();
  }

  function begin(tokenId: string, x: number, y: number): void {
    if (drag !== null) {
      pendingBegin = { tokenId, x, y, final: false };
      finishing = true;
      clearTick();
      clearBeat();
      if (!inFlight) void dispatch(true);
      return;
    }
    start(tokenId, x, y);
  }

  function move(tokenId: string, x: number, y: number): void {
    if (pendingBegin !== null && drag !== null) {
      pendingBegin = { ...pendingBegin, tokenId, x, y };
      return;
    }
    if (drag === null) {
      begin(tokenId, x, y);
      return;
    }
    drag.target = { token_id: tokenId, x, y };
    if (!inFlight && tickTimer === null) armTick();
  }

  function end(tokenId: string, x: number, y: number): void {
    if (pendingBegin !== null && drag !== null) {
      pendingBegin = { ...pendingBegin, tokenId, x, y, final: true };
      return;
    }
    if (drag !== null && finishing) {
      pendingBegin = { tokenId, x, y, final: true };
      return;
    }
    if (drag === null) begin(tokenId, x, y);
    if (drag === null) return;
    drag.target = { token_id: tokenId, x, y };
    finishing = true;
    clearTick();
    clearBeat();
    if (inFlight) armTick();
    else void dispatch(true);
  }

  function flush(): void {
    if (drag === null) return;
    finishing = true;
    clearTick();
    if (inFlight) armTick();
    else void dispatch(true);
  }

  return {
    begin,
    move,
    end,
    flush,
    active: (): boolean => drag !== null,
  };
}
