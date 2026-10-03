import { describe, expect, it } from "vitest";
import { get } from "svelte/store";
import { createAppStore } from "./store.js";
import {
  backoffDelay,
  createEventStream,
  parseFrame,
  BASE_BACKOFF_MS,
  MAX_BACKOFF_MS,
} from "./sse.js";

class FakeEventSource {
  static instances = [];

  constructor(url, options) {
    this.url = url;
    this.options = options;
    this.listeners = new Map();
    this.closed = false;
    FakeEventSource.instances.push(this);
  }

  addEventListener(type, handler) {
    const handlers = this.listeners.get(type) ?? [];
    handlers.push(handler);
    this.listeners.set(type, handlers);
  }

  emit(type, payload) {
    for (const handler of this.listeners.get(type) ?? []) {
      handler(payload);
    }
  }

  close() {
    this.closed = true;
  }
}

function harness() {
  FakeEventSource.instances = [];
  const scheduled = [];
  const events = [];
  const connection = [];
  const stream = createEventStream({
    EventSourceImpl: FakeEventSource,
    onEvent: (event) => events.push(event),
    onConnectionChange: (state) => connection.push(state),
    schedule: (fn, delay) => {
      scheduled.push({ fn, delay });
      return scheduled.length;
    },
    cancel: () => {},
  });
  return { stream, scheduled, events, connection };
}

describe("backoffDelay", () => {
  it("doubles from the base and caps at the maximum", () => {
    expect(backoffDelay(0)).toBe(BASE_BACKOFF_MS);
    expect(backoffDelay(1)).toBe(2 * BASE_BACKOFF_MS);
    expect(backoffDelay(10)).toBe(MAX_BACKOFF_MS);
  });
});

describe("parseFrame", () => {
  it("parses a JSON frame", () => {
    expect(parseFrame("status", '{"bot":{"online":true}}')).toEqual({
      type: "status",
      data: { bot: { online: true } },
    });
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
    expect(FakeEventSource.instances[0].url).toBe("/api/events");
    expect(FakeEventSource.instances[0].options).toEqual({
      withCredentials: true,
    });
  });

  it("dispatches parsed status and reload frames", () => {
    const { stream, events } = harness();
    stream.start();
    const source = FakeEventSource.instances[0];

    source.emit("status", { data: '{"bot":{"online":true}}' });
    source.emit("reload", { data: '{"scope":"shell"}' });
    source.emit("status", { data: "broken" });

    expect(events).toEqual([
      { type: "status", data: { bot: { online: true } } },
      { type: "reload", data: { scope: "shell" } },
    ]);
  });

  it("reports connection state on open and reconnect", () => {
    const { stream, scheduled, connection } = harness();
    stream.start();

    FakeEventSource.instances[0].emit("open");
    FakeEventSource.instances[0].emit("error");
    scheduled[0].fn();
    FakeEventSource.instances[1].emit("open");

    expect(connection).toEqual(["connected", "reconnecting", "connected"]);
  });

  it("reconnects with growing backoff", () => {
    const { stream, scheduled } = harness();
    stream.start();

    FakeEventSource.instances[0].emit("error");
    expect(scheduled[0].delay).toBe(BASE_BACKOFF_MS);

    scheduled[0].fn();
    FakeEventSource.instances[1].emit("error");
    expect(scheduled[1].delay).toBe(2 * BASE_BACKOFF_MS);

    scheduled[1].fn();
    FakeEventSource.instances[2].emit("error");
    expect(scheduled[2].delay).toBe(4 * BASE_BACKOFF_MS);
  });

  it("resets backoff after a successful reconnect", () => {
    const { stream, scheduled } = harness();
    stream.start();
    FakeEventSource.instances[0].emit("error");
    scheduled[0].fn();
    FakeEventSource.instances[1].emit("open");

    FakeEventSource.instances[1].emit("error");

    expect(scheduled[1].delay).toBe(BASE_BACKOFF_MS);
  });

  it("stops the current stream and any pending reconnect", () => {
    const { stream, scheduled } = harness();
    stream.start();
    FakeEventSource.instances[0].emit("error");

    stream.stop();
    scheduled[0].fn();

    expect(FakeEventSource.instances).toHaveLength(1);
    expect(FakeEventSource.instances[0].closed).toBe(true);
  });
});

describe("stream recovery", () => {
  it("resyncs the store from the full snapshot after a drop", () => {
    FakeEventSource.instances = [];
    const store = createAppStore();
    const scheduled = [];
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
    FakeEventSource.instances[0].emit("error");
    scheduled[0].fn();
    FakeEventSource.instances[1].emit("status", {
      data: JSON.stringify({
        bot: { online: true },
        guild_id: "5",
        connection: { connected: true, channel_id: "9" },
        playback: null,
      }),
    });

    expect(get(store).guildId).toBe("5");
    expect(get(store).connection.connected).toBe(true);
    expect(get(store).bot).toEqual({ online: true });
  });
});
