import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { ApiError } from "./api";
import { MOVE_LIMIT_MS, createMovePump } from "./table-moves";
import type { MoveBatch } from "./table-moves";

interface Deferred {
  promise: Promise<void>;
  resolve: () => void;
}

function deferred(): Deferred {
  let resolve: () => void = () => {};
  const promise = new Promise<void>((settle) => {
    resolve = settle;
  });
  return { promise, resolve };
}

function harness(onSend?: (batch: MoveBatch) => void) {
  const batches: MoveBatch[] = [];
  let blocked: Deferred | null = null;
  const pump = createMovePump({
    send: (batch) => {
      batches.push(batch);
      onSend?.(batch);
      return blocked === null ? Promise.resolve() : blocked.promise;
    },
  });
  return {
    pump,
    batches,
    block(): Deferred {
      const gate = deferred();
      blocked = gate;
      return gate;
    },
    unblock(gate: Deferred): void {
      blocked = null;
      gate.resolve();
    },
  };
}

beforeEach(() => {
  vi.useFakeTimers();
  vi.setSystemTime(0);
});

afterEach(() => {
  vi.useRealTimers();
});

describe("createMovePump", () => {
  it("sends the start position and coalesces to one POST in flight", async () => {
    const { pump, batches, block, unblock } = harness();
    pump.begin("tok_1", 0, 0);
    await vi.advanceTimersByTimeAsync(0);

    expect(batches).toHaveLength(1);
    expect(batches[0]?.final).toBe(false);
    expect(batches[0]?.moves).toEqual([{ token_id: "tok_1", x: 0, y: 0 }]);

    const gate = block();
    pump.move("tok_1", 1, 1);
    await vi.advanceTimersByTimeAsync(100);
    expect(batches).toHaveLength(2);

    pump.move("tok_1", 2, 2);
    pump.move("tok_1", 3, 3);
    await vi.advanceTimersByTimeAsync(500);
    expect(batches).toHaveLength(2);

    unblock(gate);
    await vi.advanceTimersByTimeAsync(1);
    expect(batches).toHaveLength(3);
    expect(batches[2]?.moves).toEqual([{ token_id: "tok_1", x: 3, y: 3 }]);
  });

  it("sends the drop as final with the last destination", async () => {
    const { pump, batches } = harness();
    pump.begin("tok_1", 0, 0);
    await vi.advanceTimersByTimeAsync(0);

    pump.move("tok_1", 2, 2);
    pump.end("tok_1", 4, 5);
    await vi.advanceTimersByTimeAsync(0);

    const last = batches.at(-1);
    expect(last?.final).toBe(true);
    expect(last?.moves).toEqual([{ token_id: "tok_1", x: 4, y: 5 }]);
    expect(pump.active()).toBe(false);
  });

  it("commits a quiet drag every five seconds", async () => {
    const { pump, batches } = harness();
    pump.begin("tok_1", 1, 1);
    await vi.advanceTimersByTimeAsync(0);

    await vi.advanceTimersByTimeAsync(5000);
    expect(batches).toHaveLength(2);
    expect(batches[1]?.final).toBe(false);
    expect(batches[1]?.moves).toEqual([{ token_id: "tok_1", x: 1, y: 1 }]);

    await vi.advanceTimersByTimeAsync(5000);
    expect(batches).toHaveLength(3);
  });

  it("falls to 1 Hz for thirty seconds after a 429 without losing the target", async () => {
    const limited: boolean[] = [];
    const batches: MoveBatch[] = [];
    const pump = createMovePump({
      send: async (batch) => {
        batches.push(batch);
        if (batches.length === 1) {
          throw new ApiError({
            code: "too_many_requests",
            message: "Too many moves",
            status: 429,
          });
        }
      },
      onLimited: (value) => limited.push(value),
    });
    pump.begin("tok_1", 0, 0);
    await vi.advanceTimersByTimeAsync(0);

    expect(limited).toEqual([true]);

    pump.move("tok_1", 1, 1);
    await vi.advanceTimersByTimeAsync(100);
    expect(batches).toHaveLength(1);

    await vi.advanceTimersByTimeAsync(900);
    expect(batches).toHaveLength(2);
    expect(batches[1]?.moves).toEqual([{ token_id: "tok_1", x: 1, y: 1 }]);

    await vi.advanceTimersByTimeAsync(MOVE_LIMIT_MS);
    expect(limited.at(-1)).toBe(false);

    pump.move("tok_1", 2, 2);
    await vi.advanceTimersByTimeAsync(100);
    expect(batches.at(-1)?.moves).toEqual([{ token_id: "tok_1", x: 2, y: 2 }]);
  });

  it("flushes the last destination as final on pagehide", async () => {
    const { pump, batches } = harness();
    pump.begin("tok_1", 0, 0);
    await vi.advanceTimersByTimeAsync(0);
    pump.move("tok_1", 1, 2);

    pump.flush();
    await vi.advanceTimersByTimeAsync(0);

    const last = batches.at(-1);
    expect(last?.final).toBe(true);
    expect(last?.moves).toEqual([{ token_id: "tok_1", x: 1, y: 2 }]);
  });
});

describe("createMovePump recovery", () => {
  it("retries the drop after a 429 instead of losing it", async () => {
    const batches: MoveBatch[] = [];
    let refusedDrop = false;
    const pump = createMovePump({
      send: async (batch) => {
        batches.push(batch);
        if (batch.final && !refusedDrop) {
          refusedDrop = true;
          throw new ApiError({
            code: "too_many_requests",
            message: "Too many moves",
            status: 429,
          });
        }
      },
    });
    pump.begin("tok_1", 0, 0);
    await vi.advanceTimersByTimeAsync(0);

    pump.end("tok_1", 5, 5);
    await vi.advanceTimersByTimeAsync(0);
    expect(batches.at(-1)?.final).toBe(true);
    expect(pump.active()).toBe(true);

    await vi.advanceTimersByTimeAsync(1000);

    expect(batches.at(-1)?.final).toBe(true);
    expect(batches.at(-1)?.moves).toEqual([{ token_id: "tok_1", x: 5, y: 5 }]);
    expect(pump.active()).toBe(false);
  });

  it("queues the final behind the in-flight POST on pagehide", async () => {
    const batches: MoveBatch[] = [];
    let blocked: Deferred | null = null;
    const pump = createMovePump({
      send: (batch) => {
        batches.push(batch);
        return blocked === null ? Promise.resolve() : blocked.promise;
      },
    });
    const gate = deferred();
    blocked = gate;
    pump.begin("tok_1", 0, 0);
    await vi.advanceTimersByTimeAsync(0);
    pump.move("tok_1", 1, 2);
    await vi.advanceTimersByTimeAsync(100);

    pump.flush();
    expect(batches).toHaveLength(1);
    expect(batches.at(-1)?.final).toBe(false);

    blocked = null;
    gate.resolve();
    await vi.advanceTimersByTimeAsync(100);

    expect(batches).toHaveLength(2);
    expect(batches.at(-1)?.final).toBe(true);
    expect(batches.at(-1)?.moves).toEqual([{ token_id: "tok_1", x: 1, y: 2 }]);
  });

  it("finishes the previous drag before starting the next one", async () => {
    const batches: MoveBatch[] = [];
    let blocked: Deferred | null = null;
    const pump = createMovePump({
      send: (batch) => {
        batches.push(batch);
        return blocked === null ? Promise.resolve() : blocked.promise;
      },
    });
    const gate = deferred();
    blocked = gate;
    pump.begin("tok_1", 0, 0);
    await vi.advanceTimersByTimeAsync(0);
    pump.move("tok_1", 1, 1);
    await vi.advanceTimersByTimeAsync(100);

    pump.begin("tok_2", 3, 3);
    pump.move("tok_2", 4, 4);
    pump.end("tok_2", 5, 5);
    await vi.advanceTimersByTimeAsync(500);
    expect(batches).toHaveLength(1);

    blocked = null;
    gate.resolve();
    await vi.advanceTimersByTimeAsync(200);

    const finals = batches.filter((batch) => batch.final);
    expect(finals.at(-1)?.moves).toEqual([{ token_id: "tok_2", x: 5, y: 5 }]);
    expect(batches.at(-1)?.moves).toEqual([{ token_id: "tok_2", x: 5, y: 5 }]);
    const firstDragFinal = batches.findIndex(
      (batch) => batch.final && batch.moves[0]?.token_id === "tok_1",
    );
    const nextStart = batches.findIndex(
      (batch) => batch.moves[0]?.token_id === "tok_2",
    );
    expect(firstDragFinal).toBeGreaterThanOrEqual(0);
    expect(firstDragFinal).toBeLessThan(nextStart);
  });

  it("keeps the 1 Hz window between drags", async () => {
    const batches: MoveBatch[] = [];
    let refused = false;
    const pump = createMovePump({
      send: async (batch) => {
        batches.push(batch);
        if (!refused) {
          refused = true;
          throw new ApiError({
            code: "too_many_requests",
            message: "Too many moves",
            status: 429,
          });
        }
      },
    });
    pump.begin("tok_1", 0, 0);
    await vi.advanceTimersByTimeAsync(0);
    pump.end("tok_1", 0, 0);
    await vi.advanceTimersByTimeAsync(1000);
    pump.begin("tok_2", 0, 0);
    await vi.advanceTimersByTimeAsync(100);

    expect(
      batches.filter((batch) => batch.moves[0]?.token_id === "tok_2"),
    ).toHaveLength(0);
    await vi.advanceTimersByTimeAsync(900);
    expect(
      batches.filter((batch) => batch.moves[0]?.token_id === "tok_2"),
    ).toHaveLength(1);
  });
});

describe("createMovePump discrete moves", () => {
  it("does not drop a move that lands while the drop is in flight", async () => {
    const batches: MoveBatch[] = [];
    let blocked: Deferred | null = deferred();
    const pump = createMovePump({
      send: (batch) => {
        batches.push(batch);
        return blocked === null ? Promise.resolve() : blocked.promise;
      },
    });
    pump.end("tok_1", 1, 0);
    pump.end("tok_1", 2, 0);

    expect(batches).toHaveLength(1);
    blocked!.resolve();
    blocked = null;
    await vi.advanceTimersByTimeAsync(200);

    expect(batches.at(-1)?.final).toBe(true);
    expect(batches.at(-1)?.moves).toEqual([{ token_id: "tok_1", x: 2, y: 0 }]);
  });
});
