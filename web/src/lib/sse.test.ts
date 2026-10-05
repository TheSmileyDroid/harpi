import { describe, expect, it } from "vitest";
import { get } from "svelte/store";
import { ApiError } from "./api";
import fixtures from "./contract/fixtures/fixtures.json";
import { createAppStore } from "./store";
import {
  backoffDelay,
  createEventStream,
  parseFrame,
  BASE_BACKOFF_MS,
  MAX_BACKOFF_MS,
  type EventSourceLike,
  type SseFrame,
} from "./sse";

const SNAPSHOT = fixtures.StatusSnapshot;
const RELOAD = fixtures.ReloadEvent;

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

  emit(type: string, payload?: { data?: string }): void {
    const event = payload as unknown as Event;
    for (const handler of this.listeners.get(type) ?? []) {
      handler(event);
    }
  }

  close(): void {
    this.closed = true;
  }
}

function harness() {
  FakeEventSource.instances = [];
  const scheduled: { fn: () => void; delay: number }[] = [];
  const events: SseFrame[] = [];
  const connection: string[] = [];
  const errors: ApiError[] = [];
  const stream = createEventStream({
    EventSourceImpl: FakeEventSource,
    onEvent: (event) => events.push(event),
    onError: (error) => errors.push(error),
    onConnectionChange: (state) => connection.push(state),
    schedule: (fn, delay) => {
      scheduled.push({ fn, delay });
      return scheduled.length;
    },
    cancel: () => {},
  });
  return { stream, scheduled, events, connection, errors };
}

describe("backoffDelay", () => {
  it("doubles from the base and caps at the maximum", () => {
    expect(backoffDelay(0)).toBe(BASE_BACKOFF_MS);
    expect(backoffDelay(1)).toBe(2 * BASE_BACKOFF_MS);
    expect(backoffDelay(10)).toBe(MAX_BACKOFF_MS);
  });
});

describe("parseFrame", () => {
  it("parses a status frame through its schema", () => {
    expect(parseFrame("status", JSON.stringify(SNAPSHOT))).toEqual({
      type: "status",
      data: SNAPSHOT,
    });
  });

  it("parses a reload frame through its schema", () => {
    expect(parseFrame("reload", JSON.stringify(RELOAD))).toEqual({
      type: "reload",
      data: RELOAD,
    });
  });

  it("drops a frame that fails its schema", () => {
    expect(parseFrame("status", '{"bot":{"online":true}}')).toBeNull();
  });

  it("drops a malformed frame", () => {
    expect(parseFrame("status", "not json")).toBeNull();
  });
});

describe("createEventStream", () => {
  it("opens one stream against the events endpoint", () => {
    const { stream } = harness();

    stream.start();

    expect(FakeEventSource.instances).toHaveLength(1);
    expect(FakeEventSource.instances[0]!.url).toBe("/api/events");
    expect(FakeEventSource.instances[0]!.options).toEqual({
      withCredentials: true,
    });
  });

  it("routes each event name to its schema", () => {
    const { stream, events, errors } = harness();
    stream.start();
    const source = FakeEventSource.instances[0]!;

    source.emit("status", { data: JSON.stringify(SNAPSHOT) });
    source.emit("reload", { data: JSON.stringify(RELOAD) });

    expect(events).toEqual([
      { type: "status", data: SNAPSHOT },
      { type: "reload", data: RELOAD },
    ]);
    expect(errors).toHaveLength(0);
  });

  it("drops an invalid frame and reports the contract violation", () => {
    const { stream, events, errors } = harness();
    stream.start();
    const source = FakeEventSource.instances[0]!;

    source.emit("status", { data: '{"bot":{"online":true}}' });
    source.emit("status", { data: "broken" });
    source.emit("reload", { data: JSON.stringify(RELOAD) });

    expect(events).toEqual([{ type: "reload", data: RELOAD }]);
    expect(errors).toHaveLength(2);
    expect(errors[0]).toBeInstanceOf(ApiError);
    expect(errors[0]!.code).toBe("contract_violation");
  });

  it("reports connection state on open and reconnect", () => {
    const { stream, scheduled, connection } = harness();
    stream.start();

    FakeEventSource.instances[0]!.emit("open");
    FakeEventSource.instances[0]!.emit("error");
    scheduled[0]!.fn();
    FakeEventSource.instances[1]!.emit("open");

    expect(connection).toEqual(["connected", "reconnecting", "connected"]);
  });

  it("reconnects with growing backoff", () => {
    const { stream, scheduled } = harness();
    stream.start();

    FakeEventSource.instances[0]!.emit("error");
    expect(scheduled[0]!.delay).toBe(BASE_BACKOFF_MS);

    scheduled[0]!.fn();
    FakeEventSource.instances[1]!.emit("error");
    expect(scheduled[1]!.delay).toBe(2 * BASE_BACKOFF_MS);

    scheduled[1]!.fn();
    FakeEventSource.instances[2]!.emit("error");
    expect(scheduled[2]!.delay).toBe(4 * BASE_BACKOFF_MS);
  });

  it("resets backoff after a successful reconnect", () => {
    const { stream, scheduled } = harness();
    stream.start();
    FakeEventSource.instances[0]!.emit("error");
    scheduled[0]!.fn();
    FakeEventSource.instances[1]!.emit("open");

    FakeEventSource.instances[1]!.emit("error");

    expect(scheduled[1]!.delay).toBe(BASE_BACKOFF_MS);
  });

  it("stops the current stream and any pending reconnect", () => {
    const { stream, scheduled } = harness();
    stream.start();
    FakeEventSource.instances[0]!.emit("error");

    stream.stop();
    scheduled[0]!.fn();

    expect(FakeEventSource.instances).toHaveLength(1);
    expect(FakeEventSource.instances[0]!.closed).toBe(true);
  });
});

describe("stream recovery", () => {
  it("resyncs the store from the full snapshot after a drop", () => {
    FakeEventSource.instances = [];
    const store = createAppStore();
    const scheduled: { fn: () => void; delay: number }[] = [];
    const stream = createEventStream({
      EventSourceImpl: FakeEventSource,
      onEvent: (event) => store.applySse(event),
      schedule: (fn, delay) => {
        scheduled.push({ fn, delay });
        return scheduled.length;
      },
      cancel: () => {},
    });

    stream.start();
    FakeEventSource.instances[0]!.emit("error");
    scheduled[0]!.fn();
    FakeEventSource.instances[1]!.emit("status", {
      data: JSON.stringify(SNAPSHOT),
    });

    expect(get(store).guildId).toBe("7");
    expect(get(store).connection.connected).toBe(true);
    expect(get(store).bot).toEqual({ online: true });
  });
});
