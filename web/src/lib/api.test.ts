import { describe, expect, it } from "vitest";
import { ApiError, createApiClient, type FetchResponse } from "./api";
import fixtures from "./contract/fixtures/fixtures.json";

const SNAPSHOT = fixtures.StatusSnapshot;

function jsonResponse(status: number, payload: unknown): FetchResponse {
  return {
    ok: status >= 200 && status < 300,
    status,
    json: async () => payload,
  };
}

function failingClient() {
  const reported: ApiError[] = [];
  const client = createApiClient({
    fetchImpl: async () => {
      throw new TypeError("fetch failed");
    },
    onError: (error) => reported.push(error),
  });
  return { client, reported };
}

function recordingClient(payload: unknown = SNAPSHOT) {
  const calls: { path: string; options: RequestInit }[] = [];
  const client = createApiClient({
    fetchImpl: async (path, options) => {
      calls.push({ path, options: options ?? {} });
      return jsonResponse(200, payload);
    },
  });
  return { client, calls };
}

describe("createApiClient", () => {
  it("exposes the discord login url without a request", () => {
    const { client, calls } = recordingClient();

    expect(client.loginUrl).toBe("/api/auth/discord");
    expect(calls).toHaveLength(0);
  });

  it("posts a logout", async () => {
    const { client, calls } = recordingClient(fixtures.Authenticated);

    await expect(client.logout()).resolves.toEqual({
      authenticated: true,
    });
    expect(calls[0]!.path).toBe("/api/logout");
    expect(calls[0]!.options.method).toBe("POST");
  });

  it("normalizes the error envelope and reports it", async () => {
    const reported: ApiError[] = [];
    const client = createApiClient({
      fetchImpl: async () =>
        jsonResponse(401, {
          error: { code: "unauthorized", message: "Authentication required" },
        }),
      onError: (error) => reported.push(error),
    });

    await expect(client.status()).rejects.toThrow("Authentication required");

    expect(reported).toHaveLength(1);
    expect(reported[0]).toBeInstanceOf(ApiError);
    expect(reported[0]!.code).toBe("unauthorized");
    expect(reported[0]!.status).toBe(401);
  });

  it("keeps the error code of a 409 that carries extra fields", async () => {
    const client = createApiClient({
      fetchImpl: async () =>
        jsonResponse(409, {
          ...fixtures.SheetConflictDetail,
        }),
    });

    await expect(
      client.writeSheet("paratheos", "sht_ana", {
        base_hash: "a".repeat(64),
      }),
    ).rejects.toMatchObject({
      code: "sheet_field_conflict",
      status: 409,
    });
  });

  it("does not report the expected unauthenticated session probe", async () => {
    const reported: ApiError[] = [];
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
        return jsonResponse(200, SNAPSHOT);
      },
    });

    await expect(client.status()).resolves.toEqual(SNAPSHOT);
  });

  it("reads the guild list", async () => {
    const client = createApiClient({
      fetchImpl: async (path) => {
        expect(path).toBe("/api/guilds");
        return jsonResponse(200, fixtures.GuildList);
      },
    });

    await expect(client.guilds()).resolves.toEqual(fixtures.GuildList);
  });

  it("reads a guild's voice channels", async () => {
    const client = createApiClient({
      fetchImpl: async (path) => {
        expect(path).toBe("/api/guilds/7/channels");
        return jsonResponse(200, fixtures.ChannelList);
      },
    });

    await expect(client.channels("7")).resolves.toEqual(fixtures.ChannelList);
  });

  it("posts a connect with the guild and channel", async () => {
    const { client, calls } = recordingClient();

    const payload = await client.connect("7", "70");

    expect(payload).toEqual(SNAPSHOT);
    expect(calls[0]!.path).toBe("/api/connect");
    expect(calls[0]!.options.method).toBe("POST");
    expect(JSON.parse(calls[0]!.options.body as string)).toEqual({
      guild_id: "7",
      channel_id: "70",
    });
  });

  it("posts a selection without connecting", async () => {
    const { client, calls } = recordingClient();

    const payload = await client.select("7", "70");

    expect(payload).toEqual(SNAPSHOT);
    expect(calls[0]!.path).toBe("/api/selection");
    expect(calls[0]!.options.method).toBe("POST");
    expect(JSON.parse(calls[0]!.options.body as string)).toEqual({
      guild_id: "7",
      channel_id: "70",
    });
  });

  it("posts an empty selection to clear the guild", async () => {
    const { client, calls } = recordingClient();

    await client.select(null, null);

    expect(JSON.parse(calls[0]!.options.body as string)).toEqual({
      guild_id: null,
      channel_id: null,
    });
  });

  it("posts a disconnect", async () => {
    const { client, calls } = recordingClient();

    await client.disconnect();

    expect(calls[0]!.path).toBe("/api/disconnect");
    expect(calls[0]!.options.method).toBe("POST");
  });

  it("posts a search term", async () => {
    const { client, calls } = recordingClient({ results: [] });

    await expect(client.search("daft punk")).resolves.toEqual({ results: [] });
    expect(calls[0]!.path).toBe("/api/search");
    expect(calls[0]!.options.method).toBe("POST");
    expect(JSON.parse(calls[0]!.options.body as string)).toEqual({
      term: "daft punk",
    });
  });

  it("posts a queue url", async () => {
    const { client, calls } = recordingClient();

    await client.queue("https://example.com/song");

    expect(calls[0]!.path).toBe("/api/queue");
    expect(calls[0]!.options.method).toBe("POST");
    expect(JSON.parse(calls[0]!.options.body as string)).toEqual({
      url: "https://example.com/song",
    });
  });

  it("posts a queue removal", async () => {
    const { client, calls } = recordingClient();

    await client.removeFromQueue("https://example.com/song");

    expect(calls[0]!.path).toBe("/api/queue/remove");
    expect(JSON.parse(calls[0]!.options.body as string)).toEqual({
      url: "https://example.com/song",
    });
  });

  it("posts a queue clear without a body", async () => {
    const { client, calls } = recordingClient();

    await client.clearQueue();

    expect(calls[0]!.path).toBe("/api/queue/clear");
    expect(calls[0]!.options.method).toBe("POST");
    expect(calls[0]!.options.body).toBeUndefined();
  });

  it("posts the bodyless transport verbs", async () => {
    for (const [method, path] of [
      ["pause", "/api/playback/pause"],
      ["resume", "/api/playback/resume"],
      ["skip", "/api/playback/skip"],
      ["previous", "/api/playback/previous"],
    ] as const) {
      const { client, calls } = recordingClient();

      await client[method]();

      expect(calls[0]!.path).toBe(path);
      expect(calls[0]!.options.method).toBe("POST");
      expect(calls[0]!.options.body).toBeUndefined();
    }
  });

  it("posts a loop mode", async () => {
    const { client, calls } = recordingClient();

    await client.loop("track");

    expect(calls[0]!.path).toBe("/api/playback/loop");
    expect(JSON.parse(calls[0]!.options.body as string)).toEqual({
      mode: "track",
    });
  });

  it("posts an absolute seek position", async () => {
    const { client, calls } = recordingClient();

    await client.seek(42.5);

    expect(calls[0]!.path).toBe("/api/playback/seek");
    expect(JSON.parse(calls[0]!.options.body as string)).toEqual({
      position: 42.5,
    });
  });

  it("posts a linear gain volume", async () => {
    const { client, calls } = recordingClient();

    await client.volume(0.25);

    expect(calls[0]!.path).toBe("/api/playback/volume");
    expect(JSON.parse(calls[0]!.options.body as string)).toEqual({
      volume: 0.25,
    });
  });

  it("posts a layer url", async () => {
    const { client, calls } = recordingClient();

    await client.layer("https://example.com/layer");

    expect(calls[0]!.path).toBe("/api/layers");
    expect(calls[0]!.options.method).toBe("POST");
    expect(JSON.parse(calls[0]!.options.body as string)).toEqual({
      url: "https://example.com/layer",
    });
  });

  it("posts a layer removal", async () => {
    const { client, calls } = recordingClient();

    await client.removeLayer("layer-1");

    expect(calls[0]!.path).toBe("/api/layers/remove");
    expect(JSON.parse(calls[0]!.options.body as string)).toEqual({
      layer_id: "layer-1",
    });
  });

  it("posts a layer volume", async () => {
    const { client, calls } = recordingClient();

    await client.setLayerVolume("layer-1", 0.25);

    expect(calls[0]!.path).toBe("/api/layers/volume");
    expect(JSON.parse(calls[0]!.options.body as string)).toEqual({
      layer_id: "layer-1",
      volume: 0.25,
    });
  });

  it("reads the campaign and its role", async () => {
    const client = createApiClient({
      fetchImpl: async (path) => {
        expect(path).toBe("/api/campaigns/paratheos");
        return jsonResponse(200, fixtures.CampaignDetail);
      },
    });

    await expect(client.campaign("paratheos")).resolves.toEqual(
      fixtures.CampaignDetail,
    );
  });

  it("creates a character from the draft", async () => {
    const { client, calls } = recordingClient(fixtures.CharacterDetail);

    await client.createCharacter("paratheos", {
      name: "Nina",
      concept: "Mensageira",
      summary: "Sem memória.",
    });

    expect(calls[0]!.path).toBe("/api/campaigns/paratheos/characters");
    expect(calls[0]!.options.method).toBe("POST");
    expect(JSON.parse(calls[0]!.options.body as string)).toEqual({
      name: "Nina",
      concept: "Mensageira",
      summary: "Sem memória.",
      sheet: null,
    });
  });

  it("submits a sheet with an empty JSON body", async () => {
    const { client, calls } = recordingClient(fixtures.CharacterDetail.sheet);

    await client.submitSheet("paratheos", "sht_ana");

    expect(calls[0]!.path).toBe(
      "/api/campaigns/paratheos/sheets/sht_ana/submit",
    );
    expect(calls[0]!.options.method).toBe("POST");
    expect(calls[0]!.options.body).toBe("{}");
    expect(calls[0]!.options.headers).toEqual({
      "Content-Type": "application/json",
    });
  });

  it("reads the approval queue", async () => {
    const client = createApiClient({
      fetchImpl: async (path) => {
        expect(path).toBe("/api/campaigns/paratheos/approvals");
        return jsonResponse(200, fixtures.ApprovalList);
      },
    });

    await expect(client.approvals("paratheos")).resolves.toEqual(
      fixtures.ApprovalList,
    );
  });

  it("decides an approval with a note", async () => {
    const { client, calls } = recordingClient(fixtures.ApprovalList);

    await client.decideApproval("paratheos", "apr_1", {
      decision: "reject",
      note: "Falta o problema.",
    });

    expect(calls[0]!.path).toBe("/api/campaigns/paratheos/approvals/apr_1");
    expect(calls[0]!.options.method).toBe("POST");
    expect(JSON.parse(calls[0]!.options.body as string)).toEqual({
      decision: "reject",
      note: "Falta o problema.",
    });
  });

  it("reads the conflict queue", async () => {
    const client = createApiClient({
      fetchImpl: async (path) => {
        expect(path).toBe("/api/campaigns/paratheos/conflicts");
        return jsonResponse(200, fixtures.SheetConflictList);
      },
    });

    await expect(client.conflicts("paratheos")).resolves.toEqual(
      fixtures.SheetConflictList,
    );
  });

  it("reads the sheet notice queue", async () => {
    const client = createApiClient({
      fetchImpl: async (path) => {
        expect(path).toBe("/api/campaigns/paratheos/notices");
        return jsonResponse(200, fixtures.SheetNoticeList);
      },
    });

    await expect(client.notices("paratheos")).resolves.toEqual(
      fixtures.SheetNoticeList,
    );
  });

  it("resolves a conflict per field", async () => {
    const { client, calls } = recordingClient(fixtures.SheetConflictList);

    await client.resolveConflict("paratheos", "cnf_1", { decision: "both" });

    expect(calls[0]!.path).toBe(
      "/api/campaigns/paratheos/conflicts/cnf_1/resolve",
    );
    expect(calls[0]!.options.method).toBe("POST");
    expect(JSON.parse(calls[0]!.options.body as string)).toEqual({
      decision: "both",
    });
  });

  it("restores and forgets a missing sheet", async () => {
    const { client, calls } = recordingClient(fixtures.CharacterDetail.sheet);

    await client.restoreSheet("paratheos", "sht_ana");

    expect(calls[0]!.path).toBe(
      "/api/campaigns/paratheos/sheets/sht_ana/restore",
    );
    expect(calls[0]!.options.body).toBe("{}");

    const forgetting = recordingClient(fixtures.SheetActionResult);
    await forgetting.client.forgetSheet("paratheos", "sht_ana");

    expect(forgetting.calls[0]!.path).toBe(
      "/api/campaigns/paratheos/sheets/sht_ana/forget",
    );
  });

  it("rejects a drifted response as a contract violation", async () => {
    const reported: ApiError[] = [];
    const client = createApiClient({
      fetchImpl: async () => jsonResponse(200, { bot: { online: true } }),
      onError: (error) => reported.push(error),
    });

    await expect(client.status()).rejects.toMatchObject({
      code: "contract_violation",
      status: 200,
    });

    expect(reported).toHaveLength(1);
    expect(reported[0]).toBeInstanceOf(ApiError);
    expect(reported[0]!.code).toBe("contract_violation");
  });

  it("keeps the session probe silent on a contract violation", async () => {
    const reported: ApiError[] = [];
    const client = createApiClient({
      fetchImpl: async () => jsonResponse(200, { authenticated: "yes" }),
      onError: (error) => reported.push(error),
    });

    await expect(client.checkSession()).rejects.toMatchObject({
      code: "contract_violation",
    });

    expect(reported).toHaveLength(0);
  });

  it("falls back to a generic envelope for an unmodeled error body", async () => {
    const reported: ApiError[] = [];
    const client = createApiClient({
      fetchImpl: async () => jsonResponse(500, { unexpected: true }),
      onError: (error) => reported.push(error),
    });

    await expect(client.status()).rejects.toMatchObject({
      code: "error",
      message: "Request failed",
      status: 500,
    });

    expect(reported).toHaveLength(1);
  });

  it("lists the scenes of a campaign", async () => {
    const client = createApiClient({
      fetchImpl: async (path) => {
        expect(path).toBe("/api/campaigns/paratheos/scenes");
        return jsonResponse(200, fixtures.SceneList);
      },
    });

    await expect(client.scenes("paratheos")).resolves.toEqual(
      fixtures.SceneList,
    );
  });

  it("opens one scene blueprint", async () => {
    const client = createApiClient({
      fetchImpl: async (path) => {
        expect(path).toBe("/api/campaigns/paratheos/scenes/cripta");
        return jsonResponse(200, fixtures.SceneDetail);
      },
    });

    await expect(client.scene("paratheos", "cripta")).resolves.toEqual(
      fixtures.SceneDetail,
    );
  });

  it("creates a scene from a vault image", async () => {
    const { client, calls } = recordingClient(fixtures.SceneDetail);

    const zones = [
      {
        id: "zon_mapa",
        label: "Mapa",
        revealed: false,
        rects: [{ x: 0, y: 0, w: 1, h: 1 }],
      },
    ];
    await client.createScene("paratheos", {
      name: "Cripta",
      source: "image",
      image: "Harpi/Campaigns/paratheos/assets/a.png",
      zones,
    });

    expect(calls[0]!.path).toBe("/api/campaigns/paratheos/scenes");
    expect(calls[0]!.options.method).toBe("POST");
    expect(JSON.parse(calls[0]!.options.body as string)).toEqual({
      name: "Cripta",
      source: "image",
      image: "Harpi/Campaigns/paratheos/assets/a.png",
      image_width: null,
      image_height: null,
      grid: null,
      fog_outside: false,
      zones,
    });
  });

  it("saves a scene with its base hash", async () => {
    const { client, calls } = recordingClient(fixtures.SceneDetail);

    await client.saveScene("paratheos", "cripta", {
      base_hash: "a".repeat(64),
      name: "Cripta",
      grid: { cell_px: 70, offset_x: 0, offset_y: 0, visible: true },
      fog_outside: true,
      zones: [
        {
          id: "zon_mapa",
          label: "Mapa",
          revealed: false,
          rects: [{ x: 0, y: 0, w: 1, h: 1 }],
        },
      ],
    });

    expect(calls[0]!.path).toBe("/api/campaigns/paratheos/scenes/cripta");
    expect(calls[0]!.options.method).toBe("PUT");
    expect(JSON.parse(calls[0]!.options.body as string)).toEqual({
      base_hash: "a".repeat(64),
      name: "Cripta",
      grid: { cell_px: 70, offset_x: 0, offset_y: 0, visible: true },
      fog_outside: true,
      zones: [
        {
          id: "zon_mapa",
          label: "Mapa",
          revealed: false,
          rects: [{ x: 0, y: 0, w: 1, h: 1 }],
        },
      ],
    });
  });

  it("uploads an image as multipart form data", async () => {
    const { client, calls } = recordingClient(fixtures.AssetDetail);
    const file = new File(["pixels"], "mapa.png", { type: "image/png" });

    await client.uploadAsset("paratheos", file);

    expect(calls[0]!.path).toBe("/api/campaigns/paratheos/assets");
    expect(calls[0]!.options.method).toBe("POST");
    expect(calls[0]!.options.body).toBeInstanceOf(FormData);
    expect((calls[0]!.options.body as FormData).get("file")).toBe(file);
  });
});
