import { describe, expect, it } from "vitest";
import { ApiError, createApiClient } from "./api.js";

function jsonResponse(status, payload) {
  return {
    ok: status >= 200 && status < 300,
    status,
    json: async () => payload,
  };
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
    const reported = [];
    const client = createApiClient({
      fetchImpl: async () => {
        throw new TypeError("fetch failed");
      },
      onError: (error) => reported.push(error),
    });

    await expect(client.status()).rejects.toMatchObject({
      code: "network_error",
      status: 0,
    });

    expect(reported).toHaveLength(1);
    expect(reported[0]).toBeInstanceOf(ApiError);
  });

  it("stays silent on a transport failure during the session probe", async () => {
    const reported = [];
    const client = createApiClient({
      fetchImpl: async () => {
        throw new TypeError("fetch failed");
      },
      onError: (error) => reported.push(error),
    });

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
});
