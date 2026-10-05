import type { z } from "zod";
import {
  Authenticated,
  ChannelList,
  ConnectRequest,
  ErrorEnvelope,
  GuildList,
  LayerIdRequest,
  LayerVolumeRequest,
  LoopRequest,
  SearchRequest,
  SearchResults,
  SeekRequest,
  SessionRequest,
  StatusSnapshot,
  UrlRequest,
  VolumeRequest,
} from "./contract/panel.gen";

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

interface RequestBaseOptions {
  method?: string;
  silent?: boolean;
}

interface RequestBodyOptions<
  Req extends z.ZodTypeAny,
> extends RequestBaseOptions {
  requestSchema: Req;
  body: z.input<Req>;
}

export function createApiClient({
  fetchImpl = (path, init) => globalThis.fetch(path, init),
  onError,
  credentials = "same-origin",
}: ApiClientOptions = {}) {
  function request<Res extends z.ZodTypeAny>(
    path: string,
    responseSchema: Res,
    options?: RequestBaseOptions,
  ): Promise<z.infer<Res>>;
  function request<Res extends z.ZodTypeAny, Req extends z.ZodTypeAny>(
    path: string,
    responseSchema: Res,
    options: RequestBodyOptions<Req>,
  ): Promise<z.infer<Res>>;
  async function request(
    path: string,
    responseSchema: z.ZodTypeAny,
    options: RequestBodyOptions<z.ZodTypeAny> | RequestBaseOptions = {},
  ): Promise<unknown> {
    const { method = "GET", silent = false } = options;
    const init: RequestInit = { method, credentials };

    if ("requestSchema" in options) {
      const wireBody = options.requestSchema.parse(options.body);
      init.headers = { "Content-Type": "application/json" };
      init.body = JSON.stringify(wireBody);
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
      const envelope = ErrorEnvelope.safeParse(payload);
      const detail = envelope.success
        ? envelope.data.error
        : { code: "error", message: "Request failed" };
      const error = new ApiError({
        code: detail.code,
        message: detail.message,
        status: response.status,
      });
      if (!silent) {
        onError?.(error);
      }
      throw error;
    }

    const parsed = responseSchema.safeParse(payload);
    if (!parsed.success) {
      const error = new ApiError({
        code: "contract_violation",
        message: `Unexpected ${method} ${path} response`,
        status: response.status,
      });
      if (!silent) {
        onError?.(error);
      }
      throw error;
    }

    return parsed.data;
  }

  return {
    signIn(token: string) {
      return request("/api/session", Authenticated, {
        method: "POST",
        requestSchema: SessionRequest,
        body: { token },
      });
    },
    checkSession() {
      return request("/api/session", Authenticated, { silent: true });
    },
    status() {
      return request("/api/status", StatusSnapshot);
    },
    guilds() {
      return request("/api/guilds", GuildList);
    },
    channels(guildId: string) {
      return request(`/api/guilds/${guildId}/channels`, ChannelList);
    },
    connect(guildId: string | null, channelId: string | null) {
      return request("/api/connect", StatusSnapshot, {
        method: "POST",
        requestSchema: ConnectRequest,
        body: { guild_id: guildId, channel_id: channelId },
      });
    },
    disconnect() {
      return request("/api/disconnect", StatusSnapshot, { method: "POST" });
    },
    search(term: string) {
      return request("/api/search", SearchResults, {
        method: "POST",
        requestSchema: SearchRequest,
        body: { term },
      });
    },
    queue(url: string) {
      return request("/api/queue", StatusSnapshot, {
        method: "POST",
        requestSchema: UrlRequest,
        body: { url },
      });
    },
    removeFromQueue(url: string) {
      return request("/api/queue/remove", StatusSnapshot, {
        method: "POST",
        requestSchema: UrlRequest,
        body: { url },
      });
    },
    clearQueue() {
      return request("/api/queue/clear", StatusSnapshot, { method: "POST" });
    },
    pause() {
      return request("/api/playback/pause", StatusSnapshot, {
        method: "POST",
      });
    },
    resume() {
      return request("/api/playback/resume", StatusSnapshot, {
        method: "POST",
      });
    },
    skip() {
      return request("/api/playback/skip", StatusSnapshot, { method: "POST" });
    },
    previous() {
      return request("/api/playback/previous", StatusSnapshot, {
        method: "POST",
      });
    },
    loop(mode: string) {
      return request("/api/playback/loop", StatusSnapshot, {
        method: "POST",
        requestSchema: LoopRequest,
        body: { mode },
      });
    },
    seek(position: number) {
      return request("/api/playback/seek", StatusSnapshot, {
        method: "POST",
        requestSchema: SeekRequest,
        body: { position },
      });
    },
    volume(volume: number) {
      return request("/api/playback/volume", StatusSnapshot, {
        method: "POST",
        requestSchema: VolumeRequest,
        body: { volume },
      });
    },
    layer(url: string) {
      return request("/api/layers", StatusSnapshot, {
        method: "POST",
        requestSchema: UrlRequest,
        body: { url },
      });
    },
    removeLayer(layerId: string) {
      return request("/api/layers/remove", StatusSnapshot, {
        method: "POST",
        requestSchema: LayerIdRequest,
        body: { layer_id: layerId },
      });
    },
    setLayerVolume(layerId: string, volume: number) {
      return request("/api/layers/volume", StatusSnapshot, {
        method: "POST",
        requestSchema: LayerVolumeRequest,
        body: { layer_id: layerId, volume },
      });
    },
  };
}

export type ApiClient = ReturnType<typeof createApiClient>;
