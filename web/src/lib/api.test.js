import { describe, expect, it } from "vitest";
import { ApiError, createApiClient } from "./api.js";

function jsonResponse(status, payload) {
  return {
    ok: status >= 200 && status < 300,
    status,
    json: async () => payload,
  };
}

function failingClient() {
  const reported = [];
  const client = createApiClient({
    fetchImpl: async () => {
      throw new TypeError("fetch failed");
    },
    onError: (error) => reported.push(error),
  });
  return { client, reported };
}

/**
 * @param {object} [payload]
 */
function recordingClient(payload = { guild_id: 7 }) {
  const calls = [];
  const client = createApiClient({
    fetchImpl: async (path, options) => {
      calls.push({ path, options });
      return jsonResponse(200, payload);
    },
  });
  return { client, calls };
}

describe("createApiClient", () => {
  it("exchanges a token for a session", async () => {
    const calls = [];
    const client = createApiClient({
      fetchImpl: async (path, options) => {
        calls.push({ path, options });
        return jsonResponse(200, { authenticated: true });
      },
    });

    const payload = await client.signIn("secret-token");

    expect(payload).toEqual({ authenticated: true });
    expect(calls[0].path).toBe("/api/session");
    expect(calls[0].options.method).toBe("POST");
    expect(JSON.parse(calls[0].options.body)).toEqual({
      token: "secret-token",
    });
    expect(calls[0].options.credentials).toBe("same-origin");
  });

  it("normalizes the error envelope and reports it", async () => {
    const reported = [];
    const client = createApiClient({
      fetchImpl: async () =>
        jsonResponse(401, {
          error: { code: "unauthorized", message: "Invalid panel token" },
        }),
      onError: (error) => reported.push(error),
    });

    await expect(client.signIn("wrong")).rejects.toThrow("Invalid panel token");

    expect(reported).toHaveLength(1);
    expect(reported[0]).toBeInstanceOf(ApiError);
    expect(reported[0].code).toBe("unauthorized");
    expect(reported[0].status).toBe(401);
  });

  it("does not report the expected unauthenticated session probe", async () => {
    const reported = [];
    const client = createApiClient({
      fetchImpl: async () =>
        jsonResponse(401, {
          error: { code: "unauthorized", message: "Authentication required" },
        }),
      onError: (error) => reported.push(error),
    });

    await expect(client.checkSession()).rejects.toBeInstanceOf(ApiError);

    expect(reported).toHaveLength(0);
  });

  it("reports a transport failure as a normalized error", async () => {
    const { client, reported } = failingClient();

    await expect(client.status()).rejects.toMatchObject({
      code: "network_error",
      status: 0,
    });

    expect(reported).toHaveLength(1);
    expect(reported[0]).toBeInstanceOf(ApiError);
  });

  it("stays silent on a transport failure during the session probe", async () => {
    const { client, reported } = failingClient();

    await expect(client.checkSession()).rejects.toMatchObject({
      code: "network_error",
    });

    expect(reported).toHaveLength(0);
  });

  it("reads the status payload", async () => {
    const client = createApiClient({
      fetchImpl: async (path) => {
        expect(path).toBe("/api/status");
        return jsonResponse(200, { bot: { online: true } });
      },
    });

    await expect(client.status()).resolves.toEqual({ bot: { online: true } });
  });

  it("reads the guild list", async () => {
    const client = createApiClient({
      fetchImpl: async (path) => {
        expect(path).toBe("/api/guilds");
        return jsonResponse(200, { guilds: [{ id: 1, name: "Alpha" }] });
      },
    });

    await expect(client.guilds()).resolves.toEqual({
      guilds: [{ id: 1, name: "Alpha" }],
    });
  });

  it("reads a guild's voice channels", async () => {
    const client = createApiClient({
      fetchImpl: async (path) => {
        expect(path).toBe("/api/guilds/7/channels");
        return jsonResponse(200, { channels: [{ id: 70, name: "Voice" }] });
      },
    });

    await expect(client.channels(7)).resolves.toEqual({
      channels: [{ id: 70, name: "Voice" }],
    });
  });

  it("posts a connect with the guild and channel", async () => {
    const { client, calls } = recordingClient({ guild_id: 7 });

    const payload = await client.connect(7, 70);

    expect(payload).toEqual({ guild_id: 7 });
    expect(calls[0].path).toBe("/api/connect");
    expect(calls[0].options.method).toBe("POST");
    expect(JSON.parse(calls[0].options.body)).toEqual({
      guild_id: 7,
      channel_id: 70,
    });
  });

  it("posts a disconnect", async () => {
    const { client, calls } = recordingClient({ guild_id: 7 });

    await client.disconnect();

    expect(calls[0].path).toBe("/api/disconnect");
    expect(calls[0].options.method).toBe("POST");
  });

  it("posts a search term", async () => {
    const { client, calls } = recordingClient({ results: [] });

    await expect(client.search("daft punk")).resolves.toEqual({ results: [] });
    expect(calls[0].path).toBe("/api/search");
    expect(calls[0].options.method).toBe("POST");
    expect(JSON.parse(calls[0].options.body)).toEqual({ term: "daft punk" });
  });

  it("posts a queue url", async () => {
    const { client, calls } = recordingClient({ guild_id: 7 });

    await client.queue("https://example.com/song");

    expect(calls[0].path).toBe("/api/queue");
    expect(calls[0].options.method).toBe("POST");
    expect(JSON.parse(calls[0].options.body)).toEqual({
      url: "https://example.com/song",
    });
  });

  it("posts a queue removal", async () => {
    const { client, calls } = recordingClient({ guild_id: 7 });

    await client.removeFromQueue("https://example.com/song");

    expect(calls[0].path).toBe("/api/queue/remove");
    expect(JSON.parse(calls[0].options.body)).toEqual({
      url: "https://example.com/song",
    });
  });

  it("posts a queue clear without a body", async () => {
    const { client, calls } = recordingClient({ guild_id: 7 });

    await client.clearQueue();

    expect(calls[0].path).toBe("/api/queue/clear");
    expect(calls[0].options.method).toBe("POST");
    expect(calls[0].options.body).toBeUndefined();
  });
});
