import type {
  Authenticated,
  ChannelList,
  GuildList,
  SearchResults,
  StatusSnapshot,
} from "./types";

export class ApiError extends Error {
  code: string;
  status: number;

  constructor({
    code,
    message,
    status,
  }: {
    code: string;
    message: string;
    status: number;
  }) {
    super(message);
    this.name = "ApiError";
    this.code = code;
    this.status = status;
  }
}

export interface FetchResponse {
  ok: boolean;
  status: number;
  json: () => Promise<unknown>;
}

type FetchImpl = (path: string, init?: RequestInit) => Promise<FetchResponse>;

export interface ApiClientOptions {
  fetchImpl?: FetchImpl;
  onError?: (error: ApiError) => void;
  credentials?: RequestCredentials;
}

interface RequestOptions {
  method?: string;
  body?: unknown;
  silent?: boolean;
}

export function createApiClient({
  fetchImpl = (path, init) => globalThis.fetch(path, init),
  onError,
  credentials = "same-origin",
}: ApiClientOptions = {}) {
  async function request<T>(
    path: string,
    { method = "GET", body, silent = false }: RequestOptions = {},
  ): Promise<T> {
    const init: RequestInit = { method, credentials };
    if (body !== undefined) {
      init.headers = { "Content-Type": "application/json" };
      init.body = JSON.stringify(body);
    }

    let response: FetchResponse;
    try {
      response = await fetchImpl(path, init);
    } catch {
      const error = new ApiError({
        code: "network_error",
        message: "Cannot reach the panel API",
        status: 0,
      });
      if (!silent) {
        onError?.(error);
      }
      throw error;
    }

    let payload: unknown = null;
    try {
      payload = await response.json();
    } catch {
      payload = null;
    }

    if (!response.ok) {
      const envelope = (
        payload as { error?: { code?: string; message?: string } } | null
      )?.error ?? {
        code: "error",
        message: "Request failed",
      };
      const error = new ApiError({
        code: envelope.code ?? "error",
        message: envelope.message ?? "Request failed",
        status: response.status,
      });
      if (!silent) {
        onError?.(error);
      }
      throw error;
    }

    return payload as T;
  }

  return {
    signIn(token: string) {
      return request<Authenticated>("/api/session", {
        method: "POST",
        body: { token },
      });
    },
    checkSession() {
      return request<Authenticated>("/api/session", { silent: true });
    },
    status() {
      return request<StatusSnapshot>("/api/status");
    },
    guilds() {
      return request<GuildList>("/api/guilds");
    },
    channels(guildId: string) {
      return request<ChannelList>(`/api/guilds/${guildId}/channels`);
    },
    connect(guildId: string | null, channelId: string | null) {
      return request<StatusSnapshot>("/api/connect", {
        method: "POST",
        body: { guild_id: guildId, channel_id: channelId },
      });
    },
    disconnect() {
      return request<StatusSnapshot>("/api/disconnect", { method: "POST" });
    },
    search(term: string) {
      return request<SearchResults>("/api/search", {
        method: "POST",
        body: { term },
      });
    },
    queue(url: string) {
      return request<StatusSnapshot>("/api/queue", {
        method: "POST",
        body: { url },
      });
    },
    removeFromQueue(url: string) {
      return request<StatusSnapshot>("/api/queue/remove", {
        method: "POST",
        body: { url },
      });
    },
    clearQueue() {
      return request<StatusSnapshot>("/api/queue/clear", { method: "POST" });
    },
    pause() {
      return request<StatusSnapshot>("/api/playback/pause", {
        method: "POST",
      });
    },
    resume() {
      return request<StatusSnapshot>("/api/playback/resume", {
        method: "POST",
      });
    },
    skip() {
      return request<StatusSnapshot>("/api/playback/skip", { method: "POST" });
    },
    previous() {
      return request<StatusSnapshot>("/api/playback/previous", {
        method: "POST",
      });
    },
    loop(mode: string) {
      return request<StatusSnapshot>("/api/playback/loop", {
        method: "POST",
        body: { mode },
      });
    },
    seek(position: number) {
      return request<StatusSnapshot>("/api/playback/seek", {
        method: "POST",
        body: { position },
      });
    },
    volume(volume: number) {
      return request<StatusSnapshot>("/api/playback/volume", {
        method: "POST",
        body: { volume },
      });
    },
    layer(url: string) {
      return request<StatusSnapshot>("/api/layers", {
        method: "POST",
        body: { url },
      });
    },
    removeLayer(layerId: string) {
      return request<StatusSnapshot>("/api/layers/remove", {
        method: "POST",
        body: { layer_id: layerId },
      });
    },
    setLayerVolume(layerId: string, volume: number) {
      return request<StatusSnapshot>("/api/layers/volume", {
        method: "POST",
        body: { layer_id: layerId, volume },
      });
    },
  };
}

export type ApiClient = ReturnType<typeof createApiClient>;
