import { describe, expect, it, vi } from "vitest";
import { get } from "svelte/store";
import fixtures from "./contract/fixtures/fixtures.json";
import type {
  TableRoll,
  TableSheetChanged,
  TableStreamSnapshot,
  TableStreamViewers,
} from "./contract/panel.gen";
import {
  createTableLiveStore,
  initialTableLive,
  reduceTableFrame,
  startTableStream,
} from "./table-stream";
import type { TableSseFrame } from "./sse";
import type { AwakeTargets, EventSourceLike } from "./sse";

const SNAPSHOT = fixtures.TableStreamSnapshot as TableStreamSnapshot;
const DELTA = fixtures.TableStreamDelta;
const VIEWERS = fixtures.TableStreamViewers as TableStreamViewers;
const SHEET = fixtures.TableSheetChanged as TableSheetChanged;
const ROLL = fixtures.TableRoll as TableRoll;
const CLOSED = { reason: "A mesa foi fechada." };

class FakeEventSource implements EventSourceLike {
  static instances: FakeEventSource[] = [];

  url: string;
  options: { withCredentials?: boolean } | undefined;
  listeners = new Map<string, ((event: Event) => void)[]>();
  closed = false;

  constructor(url: string, options?: { withCredentials?: boolean }) {
    this.url = url;
    this.options = options;
    this.listeners = new Map();
    this.closed = false;
    FakeEventSource.instances.push(this);
  }

  addEventListener(type: string, handler: (event: Event) => void): void {
    const handlers = this.listeners.get(type) ?? [];
    handlers.push(handler);
    this.listeners.set(type, handlers);
  }

  emit(type: string, payload: { data?: string }): void {
    const event = payload as unknown as Event;
    for (const handler of this.listeners.get(type) ?? []) {
      handler(event);
    }
  }

  close(): void {
    this.closed = true;
  }
}

function snapshotFrame(rev = SNAPSHOT.stream_rev): TableSseFrame {
  return {
    type: "table.snapshot",
    data: { ...SNAPSHOT, stream_rev: rev },
  } as TableSseFrame;
}

function deltaFrame(
  from: number,
  to: number,
  overrides: Record<string, unknown> = {},
): TableSseFrame {
  return {
    type: "table.delta",
    data: {
      ...DELTA,
      from_stream_rev: from,
      stream_rev: to,
      ...overrides,
    },
  } as TableSseFrame;
}

describe("reduceTableFrame", () => {
  it("adopts the snapshot revision, state and roster", () => {
    const outcome = reduceTableFrame(initialTableLive(), snapshotFrame());

    expect(outcome.diverged).toBe(false);
    expect(outcome.state.streamRev).toBe(SNAPSHOT.stream_rev);
    expect(outcome.state.summary?.id).toBe(SNAPSHOT.state.id);
    expect(outcome.state.viewers).toEqual(SNAPSHOT.viewers);
  });

  it("applies a delta in order and drops a removed token", () => {
    const start = reduceTableFrame(initialTableLive(), snapshotFrame(4));
    const token = SNAPSHOT.state.tokens[0]!;
    const outcome = reduceTableFrame(
      start.state,
      deltaFrame(4, 5, {
        tokens: [{ ...token, x: 6 }],
        removed: [],
      }),
    );

    expect(outcome.diverged).toBe(false);
    expect(outcome.state.streamRev).toBe(5);
    expect(
      outcome.state.summary?.tokens.find((item) => item.id === token.id)?.x,
    ).toBe(6);
  });

  it("replaces absolute entities from the delta", () => {
    const start = reduceTableFrame(initialTableLive(), snapshotFrame(4));
    const outcome = reduceTableFrame(
      start.state,
      deltaFrame(4, 5, { round: 3, status: "open", removed: [] }),
    );

    expect(outcome.state.summary?.round).toBe(3);
  });

  it("flags a delta that arrives out of order", () => {
    const start = reduceTableFrame(initialTableLive(), snapshotFrame(4));
    const outcome = reduceTableFrame(start.state, deltaFrame(2, 3));

    expect(outcome.diverged).toBe(true);
    expect(outcome.state.streamRev).toBe(4);
  });

  it("flags a delta for another scene", () => {
    const start = reduceTableFrame(initialTableLive(), snapshotFrame(4));
    const outcome = reduceTableFrame(
      start.state,
      deltaFrame(4, 5, { scene_id: "scn_other" }),
    );

    expect(outcome.diverged).toBe(true);
  });

  it("flags a delta before any snapshot", () => {
    const outcome = reduceTableFrame(initialTableLive(), deltaFrame(0, 1));

    expect(outcome.diverged).toBe(true);
  });

  it("updates the roster and tracks drags by token", () => {
    const start = reduceTableFrame(initialTableLive(), snapshotFrame());
    const withDrag = reduceTableFrame(start.state, {
      type: "table.drag",
      data: { token_id: "tok_1", actor: "Ana", active: true },
    });
    const withoutDrag = reduceTableFrame(withDrag.state, {
      type: "table.drag",
      data: { token_id: "tok_1", actor: "Ana", active: false },
    });
    const viewers = reduceTableFrame(withoutDrag.state, {
      type: "table.viewers",
      data: VIEWERS,
    });

    expect(withDrag.state.drags).toEqual([
      { token_id: "tok_1", actor: "Ana", active: true },
    ]);
    expect(withoutDrag.state.drags).toEqual([]);
    expect(viewers.state.viewers).toEqual(VIEWERS.viewers);
  });

  it("appends a table.roll frame and dedupes it by id", () => {
    const frame = { type: "table.roll", data: ROLL } as TableSseFrame;
    const start = reduceTableFrame(initialTableLive(), snapshotFrame());
    const first = reduceTableFrame(start.state, frame);
    const again = reduceTableFrame(first.state, frame);

    expect(again.state.rolls).toEqual([ROLL]);
  });

  it("ignores a table.roll from another table", () => {
    const start = reduceTableFrame(initialTableLive(), snapshotFrame());
    const stale = {
      type: "table.roll",
      data: { ...ROLL, table_id: "tbl_previous" },
    } as TableSseFrame;
    const after = reduceTableFrame(start.state, stale);

    expect(after.state.rolls).toEqual([]);
  });

  it("keeps the log for one table and clears it on a table change", () => {
    const store = createTableLiveStore();
    const first = { ...SNAPSHOT.state, id: "tbl_first" };
    store.setSummary(first);
    store.addRolls([ROLL]);
    store.setSummary({ ...first });
    expect(get(store).rolls).toEqual([ROLL]);
    store.setSummary({ ...first, id: "tbl_second" });
    expect(get(store).rolls).toEqual([]);
  });

  it("keeps the latest sheet change per sheet", () => {
    const start = reduceTableFrame(initialTableLive(), snapshotFrame());
    const first = reduceTableFrame(start.state, {
      type: "sheet.changed",
      data: SHEET,
    });
    const second = reduceTableFrame(first.state, {
      type: "sheet.changed",
      data: { ...SHEET, rev: SHEET.rev + 1 },
    });

    expect(second.state.sheetChanges).toHaveLength(1);
    expect(second.state.sheetChanges[0]?.rev).toBe(SHEET.rev + 1);
  });

  it("marks the table closed and the stream finished", () => {
    const start = reduceTableFrame(initialTableLive(), snapshotFrame());
    const outcome = reduceTableFrame(start.state, {
      type: "table.closed",
      data: CLOSED,
    });

    expect(outcome.closed).toBe(true);
    expect(outcome.state.closedReason).toBe(CLOSED.reason);
    expect(outcome.state.summary?.status).toBe("closed");
  });
});

function wiredStore(onClosed?: () => void) {
  FakeEventSource.instances = [];
  const scheduled: { fn: () => void; delay: number }[] = [];
  const store = createTableLiveStore();
  const stream = startTableStream({
    tableId: "tbl_1",
    store,
    EventSourceImpl: FakeEventSource,
    schedule: (fn, delay) => {
      scheduled.push({ fn, delay });
      return scheduled.length;
    },
    cancel: () => {},
    awake: null,
    ...(onClosed ? { onClosed } : {}),
  });
  return { stream, store, scheduled };
}

describe("startTableStream", () => {
  it("opens the table events url with credentials", () => {
    const { stream } = wiredStore();

    expect(FakeEventSource.instances[0]!.url).toBe("/api/tables/tbl_1/events");
    expect(FakeEventSource.instances[0]!.options).toEqual({
      withCredentials: true,
    });
    stream.stop();
  });

  it("adopts a snapshot and applies the next delta", () => {
    const { stream, store } = wiredStore();
    const source = FakeEventSource.instances[0]!;

    source.emit("table.snapshot", { data: JSON.stringify(SNAPSHOT) });
    source.emit("table.delta", {
      data: JSON.stringify({
        ...DELTA,
        from_stream_rev: SNAPSHOT.stream_rev,
        stream_rev: SNAPSHOT.stream_rev + 1,
        tokens: [],
        removed: [],
      }),
    });

    expect(get(store).streamRev).toBe(SNAPSHOT.stream_rev + 1);
    expect(get(store).summary?.id).toBe(SNAPSHOT.state.id);
    stream.stop();
  });

  it("reconnects with backoff when a delta diverges", () => {
    const { stream, store, scheduled } = wiredStore();
    FakeEventSource.instances[0]!.emit("table.snapshot", {
      data: JSON.stringify(SNAPSHOT),
    });
    FakeEventSource.instances[0]!.emit("table.delta", {
      data: JSON.stringify({ ...DELTA, from_stream_rev: 0, stream_rev: 99 }),
    });

    expect(FakeEventSource.instances).toHaveLength(1);
    expect(FakeEventSource.instances[0]!.closed).toBe(true);
    expect(scheduled.some((timer) => timer.delay === 1000)).toBe(true);
    expect(get(store).streamRev).toBe(SNAPSHOT.stream_rev);
    stream.stop();
  });

  it("stops and reports a closed table once", () => {
    const closed = vi.fn();
    const { stream, store } = wiredStore(closed);
    const source = FakeEventSource.instances[0]!;
    source.emit("table.snapshot", { data: JSON.stringify(SNAPSHOT) });

    source.emit("table.closed", { data: JSON.stringify(CLOSED) });

    expect(get(store).closedReason).toBe(CLOSED.reason);
    expect(source.closed).toBe(true);
    expect(closed).toHaveBeenCalledTimes(1);
    store.setSummary({ ...SNAPSHOT.state, status: "open" });
    expect(get(store).closedReason).toBeNull();
    stream.stop();
  });
});

function fakeAwake() {
  const listeners = new Map<string, (() => void)[]>();
  const target = {
    addEventListener: (type: string, listener: () => void) => {
      listeners.set(type, [...(listeners.get(type) ?? []), listener]);
    },
    removeEventListener: (type: string, listener: () => void) => {
      listeners.set(
        type,
        (listeners.get(type) ?? []).filter((item) => item !== listener),
      );
    },
    fire: (type: string) => {
      for (const listener of listeners.get(type) ?? []) listener();
    },
    count: (type: string) => (listeners.get(type) ?? []).length,
  };
  const document = { ...target, visibilityState: "visible" };
  const awake: AwakeTargets = { document, window: target };
  return { awake, document, target };
}

describe("table stream recovery", () => {
  it("reconnects when the tab becomes visible again", () => {
    FakeEventSource.instances = [];
    const { awake, document } = fakeAwake();
    const store = createTableLiveStore();
    const stream = startTableStream({
      tableId: "tbl_1",
      store,
      EventSourceImpl: FakeEventSource,
      schedule: () => 1,
      cancel: () => {},
      awake,
    });

    document.fire("visibilitychange");

    expect(FakeEventSource.instances.length).toBeGreaterThan(1);
    stream.stop();
    expect(document.count("visibilitychange")).toBe(0);
  });

  it("reconnects when the browser comes back online", () => {
    FakeEventSource.instances = [];
    const { awake, target } = fakeAwake();
    const stream = startTableStream({
      tableId: "tbl_1",
      store: createTableLiveStore(),
      EventSourceImpl: FakeEventSource,
      schedule: () => 1,
      cancel: () => {},
      awake,
    });

    target.fire("online");

    expect(FakeEventSource.instances.length).toBeGreaterThan(1);
    stream.stop();
    expect(target.count("online")).toBe(0);
  });
});

describe("drag markers and the local drag", () => {
  function manualStore() {
    const tasks = new Map<number, () => void>();
    let sequence = 0;
    const store = createTableLiveStore({
      schedule: (fn) => {
        sequence += 1;
        tasks.set(sequence, fn);
        return sequence as unknown as ReturnType<typeof setTimeout>;
      },
      cancel: (id) => {
        tasks.delete(id as unknown as number);
      },
    });
    function fire(): void {
      for (const [id, fn] of [...tasks]) {
        tasks.delete(id);
        fn();
      }
    }
    return { store, tasks, fire };
  }

  it("drops a drag marker when its three seconds run out", () => {
    const { store, tasks, fire } = manualStore();
    store.apply(snapshotFrame());
    store.apply({
      type: "table.drag",
      data: { token_id: "tok_1", actor: "Ana", active: true },
    });

    expect(get(store).drags).toHaveLength(1);
    expect(tasks.size).toBe(1);

    fire();

    expect(get(store).drags).toEqual([]);
  });

  it("renews the marker on each drag frame and clears it on the drop", () => {
    const { store, tasks, fire } = manualStore();
    store.apply(snapshotFrame());
    const start = {
      type: "table.drag" as const,
      data: { token_id: "tok_1", actor: "Ana", active: true },
    };
    store.apply(start);
    const first = [...tasks.keys()];
    store.apply(start);

    expect(first.every((id) => !tasks.has(id))).toBe(true);
    expect(get(store).drags).toHaveLength(1);

    store.apply({
      type: "table.drag",
      data: { token_id: "tok_1", actor: "Ana", active: false },
    });

    expect(get(store).drags).toEqual([]);
    expect(tasks.size).toBe(0);
    fire();
  });

  it("keeps the local position while the same token is being dragged", () => {
    const { store } = manualStore();
    store.apply(snapshotFrame());
    store.setLocalDrag("tok_1");
    const outcome = store.apply(
      deltaFrame(4, 5, {
        tokens: [{ ...SNAPSHOT.state.tokens[0]!, x: 9, y: 9 }],
      }),
    );

    expect(outcome.diverged).toBe(false);
    expect(get(store).streamRev).toBe(5);
    expect(get(store).summary?.tokens[0]?.x).toBe(SNAPSHOT.state.tokens[0]?.x);

    store.setLocalDrag(null);
    store.apply(
      deltaFrame(5, 6, {
        tokens: [{ ...SNAPSHOT.state.tokens[0]!, x: 9, y: 9 }],
      }),
    );
    expect(get(store).summary?.tokens[0]?.x).toBe(9);
  });
});

describe("the local drag in the store", () => {
  it("moves the token locally before the server confirms", () => {
    const store = createTableLiveStore();
    store.apply(snapshotFrame());
    store.setLocalDrag("tok_1");

    store.moveLocal("tok_1", 6, 7);

    const token = get(store).summary?.tokens.find((t) => t.id === "tok_1");
    expect([token?.x, token?.y]).toEqual([6, 7]);
  });

  it("removes a token deleted mid-drag only after the drag ends", () => {
    const store = createTableLiveStore();
    store.apply(snapshotFrame());
    store.setLocalDrag("tok_1");
    store.apply(deltaFrame(4, 5, { removed: ["tok_1"], tokens: [] }));

    expect(get(store).summary?.tokens).toHaveLength(1);

    store.setLocalDrag(null);

    expect(get(store).summary?.tokens).toEqual([]);
  });

  it("keeps a pending removal when another drag starts before it clears", () => {
    const store = createTableLiveStore();
    store.apply(snapshotFrame());
    store.setLocalDrag("tok_1");
    store.apply(deltaFrame(4, 5, { removed: ["tok_1"], tokens: [] }));
    store.setLocalDrag(null);

    expect(get(store).summary?.tokens).toEqual([]);
    expect(get(store).pendingRemovals).toEqual([]);
  });
});
