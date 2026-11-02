import type { z } from "zod";
import {
  ApprovalDecision,
  ApprovalList,
  AssetDetail,
  Authenticated,
  CampaignDetail,
  ChannelList,
  CharacterCreate,
  CharacterDetail,
  CharacterList,
  ConnectRequest,
  ErrorEnvelope,
  GuildList,
  LayerIdRequest,
  LayerVolumeRequest,
  LoopRequest,
  SearchRequest,
  SearchResults,
  SeekRequest,
  SheetActionResult,
  SheetConflictDecision,
  SheetConflictList,
  SheetDetail,
  SheetPatch,
  SceneCreate,
  SceneDetail,
  SceneList,
  SceneSave,
  StatusSnapshot,
  TableMoves,
  TableMovesResult,
  TableOpen,
  TableRollCreate,
  TableRollList,
  TableSceneChange,
  TableSpectators,
  TableSummary,
  TableTokenCreate,
  TableTokenPatch,
  TableTurnRequest,
  UrlRequest,
  VolumeRequest,
} from "./contract/panel.gen";

function errorDetail(payload: unknown): { code: string; message: string } {
  const envelope = ErrorEnvelope.safeParse(payload);
  if (envelope.success) return envelope.data.error;
  const error = (payload as { error?: { code?: unknown; message?: unknown } })
    ?.error;
  if (typeof error?.code === "string" && typeof error.message === "string") {
    return { code: error.code, message: error.message };
  }
  return { code: "error", message: "Request failed" };
}

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
  json?: boolean;
  formData?: FormData;
  keepalive?: boolean;
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
    const {
      method = "GET",
      silent = false,
      json = false,
      keepalive = false,
    } = options;
    const init: RequestInit = { method, credentials };

    if (keepalive) {
      init.keepalive = true;
    }

    if ("requestSchema" in options) {
      const wireBody = options.requestSchema.parse(options.body);
      init.headers = { "Content-Type": "application/json" };
      init.body = JSON.stringify(wireBody);
    } else if (options.formData) {
      init.body = options.formData;
    } else if (json) {
      init.headers = { "Content-Type": "application/json" };
      init.body = "{}";
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
      const detail = errorDetail(payload);
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
        message: "The panel got an unexpected response",
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
    loginUrl: "/api/auth/discord",
    checkSession() {
      return request("/api/session", Authenticated, { silent: true });
    },
    logout() {
      return request("/api/logout", Authenticated, { method: "POST" });
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
    campaignCharacters(slug: string) {
      return request(
        `/api/campaigns/${encodeURIComponent(slug)}/characters`,
        CharacterList,
      );
    },
    campaign(slug: string) {
      return request(
        `/api/campaigns/${encodeURIComponent(slug)}`,
        CampaignDetail,
      );
    },
    createCharacter(slug: string, body: z.input<typeof CharacterCreate>) {
      return request(
        `/api/campaigns/${encodeURIComponent(slug)}/characters`,
        CharacterDetail,
        {
          method: "POST",
          requestSchema: CharacterCreate,
          body,
          silent: true,
        },
      );
    },
    submitSheet(slug: string, sheetId: string) {
      return request(
        `/api/campaigns/${encodeURIComponent(slug)}/sheets/${encodeURIComponent(sheetId)}/submit`,
        SheetDetail,
        { method: "POST", json: true, silent: true },
      );
    },
    approvals(slug: string) {
      return request(
        `/api/campaigns/${encodeURIComponent(slug)}/approvals`,
        ApprovalList,
      );
    },
    decideApproval(
      slug: string,
      approvalId: string,
      body: z.input<typeof ApprovalDecision>,
    ) {
      return request(
        `/api/campaigns/${encodeURIComponent(slug)}/approvals/${encodeURIComponent(approvalId)}`,
        ApprovalList,
        {
          method: "POST",
          requestSchema: ApprovalDecision,
          body,
          silent: true,
        },
      );
    },
    conflicts(slug: string) {
      return request(
        `/api/campaigns/${encodeURIComponent(slug)}/conflicts`,
        SheetConflictList,
      );
    },
    resolveConflict(
      slug: string,
      conflictId: string,
      body: z.input<typeof SheetConflictDecision>,
    ) {
      return request(
        `/api/campaigns/${encodeURIComponent(slug)}/conflicts/${encodeURIComponent(conflictId)}/resolve`,
        SheetConflictList,
        {
          method: "POST",
          requestSchema: SheetConflictDecision,
          body,
          silent: true,
        },
      );
    },
    restoreSheet(slug: string, sheetId: string) {
      return request(
        `/api/campaigns/${encodeURIComponent(slug)}/sheets/${encodeURIComponent(sheetId)}/restore`,
        SheetDetail,
        { method: "POST", json: true, silent: true },
      );
    },
    forgetSheet(slug: string, sheetId: string) {
      return request(
        `/api/campaigns/${encodeURIComponent(slug)}/sheets/${encodeURIComponent(sheetId)}/forget`,
        SheetActionResult,
        { method: "POST", json: true, silent: true },
      );
    },
    campaignCharacter(slug: string, characterId: string) {
      return request(
        `/api/campaigns/${encodeURIComponent(slug)}/characters/${encodeURIComponent(characterId)}`,
        CharacterDetail,
      );
    },
    scenes(slug: string) {
      return request(
        `/api/campaigns/${encodeURIComponent(slug)}/scenes`,
        SceneList,
      );
    },
    scene(slug: string, scene: string) {
      return request(
        `/api/campaigns/${encodeURIComponent(slug)}/scenes/${encodeURIComponent(scene)}`,
        SceneDetail,
      );
    },
    createScene(slug: string, body: z.input<typeof SceneCreate>) {
      return request(
        `/api/campaigns/${encodeURIComponent(slug)}/scenes`,
        SceneDetail,
        {
          method: "POST",
          requestSchema: SceneCreate,
          body,
          silent: true,
        },
      );
    },
    saveScene(slug: string, scene: string, body: z.input<typeof SceneSave>) {
      return request(
        `/api/campaigns/${encodeURIComponent(slug)}/scenes/${encodeURIComponent(scene)}`,
        SceneDetail,
        {
          method: "PUT",
          requestSchema: SceneSave,
          body,
          silent: true,
        },
      );
    },
    uploadAsset(slug: string, file: File) {
      const form = new FormData();
      form.append("file", file);
      return request(
        `/api/campaigns/${encodeURIComponent(slug)}/assets`,
        AssetDetail,
        { method: "POST", formData: form, silent: true },
      );
    },
    writeSheet(
      slug: string,
      sheetId: string,
      body: z.input<typeof SheetPatch>,
    ) {
      return request(
        `/api/campaigns/${encodeURIComponent(slug)}/sheets/${encodeURIComponent(sheetId)}`,
        SheetDetail,
        {
          method: "PATCH",
          requestSchema: SheetPatch,
          body,
          silent: true,
        },
      );
    },
    tableSummary(tableId: string) {
      return request(
        `/api/tables/${encodeURIComponent(tableId)}/summary`,
        TableSummary,
      );
    },
    openTable(body: z.input<typeof TableOpen>) {
      return request("/api/tables", TableSummary, {
        method: "POST",
        requestSchema: TableOpen,
        body,
        silent: true,
      });
    },
    closeTable(tableId: string) {
      return request(
        `/api/tables/${encodeURIComponent(tableId)}/close`,
        TableSummary,
        { method: "POST", json: true, silent: true },
      );
    },
    reopenTable(tableId: string) {
      return request(
        `/api/tables/${encodeURIComponent(tableId)}/reopen`,
        TableSummary,
        { method: "POST", json: true, silent: true },
      );
    },
    changeTableScene(tableId: string, body: z.input<typeof TableSceneChange>) {
      return request(
        `/api/tables/${encodeURIComponent(tableId)}/scene`,
        TableSummary,
        {
          method: "POST",
          requestSchema: TableSceneChange,
          body,
          silent: true,
        },
      );
    },
    reloadTableScene(tableId: string) {
      return request(
        `/api/tables/${encodeURIComponent(tableId)}/scene/reload`,
        TableSummary,
        { method: "POST", json: true, silent: true },
      );
    },
    revealZone(tableId: string, zoneId: string) {
      return request(
        `/api/tables/${encodeURIComponent(tableId)}/zones/${encodeURIComponent(zoneId)}/reveal`,
        TableSummary,
        { method: "POST", json: true, silent: true },
      );
    },
    hideZone(tableId: string, zoneId: string) {
      return request(
        `/api/tables/${encodeURIComponent(tableId)}/zones/${encodeURIComponent(zoneId)}/hide`,
        TableSummary,
        { method: "POST", json: true, silent: true },
      );
    },
    createTableToken(tableId: string, body: z.input<typeof TableTokenCreate>) {
      return request(
        `/api/tables/${encodeURIComponent(tableId)}/tokens`,
        TableSummary,
        {
          method: "POST",
          requestSchema: TableTokenCreate,
          body,
          silent: true,
        },
      );
    },
    patchTableToken(
      tableId: string,
      tokenId: string,
      body: z.input<typeof TableTokenPatch>,
    ) {
      return request(
        `/api/tables/${encodeURIComponent(tableId)}/tokens/${encodeURIComponent(tokenId)}`,
        TableSummary,
        {
          method: "PATCH",
          requestSchema: TableTokenPatch,
          body,
          silent: true,
        },
      );
    },
    deleteTableToken(tableId: string, tokenId: string) {
      return request(
        `/api/tables/${encodeURIComponent(tableId)}/tokens/${encodeURIComponent(tokenId)}`,
        TableSummary,
        { method: "DELETE", json: true, silent: true },
      );
    },
    tableTurn(tableId: string, body: z.input<typeof TableTurnRequest>) {
      return request(
        `/api/tables/${encodeURIComponent(tableId)}/turns`,
        TableSummary,
        {
          method: "POST",
          requestSchema: TableTurnRequest,
          body,
          silent: true,
        },
      );
    },
    tableMoves(tableId: string, body: z.input<typeof TableMoves>) {
      return request(
        `/api/tables/${encodeURIComponent(tableId)}/moves`,
        TableMovesResult,
        {
          method: "POST",
          requestSchema: TableMoves,
          body,
          silent: true,
          keepalive: true,
        },
      );
    },
    setTableSpectators(tableId: string, body: z.input<typeof TableSpectators>) {
      return request(
        `/api/tables/${encodeURIComponent(tableId)}/spectators`,
        TableSummary,
        {
          method: "POST",
          requestSchema: TableSpectators,
          body,
          silent: true,
        },
      );
    },
    tableRolls(tableId: string, after: string | null = null, limit = 50) {
      const query = new URLSearchParams({ limit: String(limit) });
      if (after !== null) query.set("after", after);
      return request(
        `/api/tables/${encodeURIComponent(tableId)}/rolls?${query.toString()}`,
        TableRollList,
      );
    },
    postTableRoll(tableId: string, body: z.input<typeof TableRollCreate>) {
      return request(
        `/api/tables/${encodeURIComponent(tableId)}/rolls`,
        TableRollList,
        {
          method: "POST",
          requestSchema: TableRollCreate,
          body,
          silent: true,
        },
      );
    },
    connect(guildId: string | null, channelId: string | null) {
      return request("/api/connect", StatusSnapshot, {
        method: "POST",
        requestSchema: ConnectRequest,
        body: { guild_id: guildId, channel_id: channelId },
      });
    },
    select(guildId: string | null, channelId: string | null, silent = false) {
      return request("/api/selection", StatusSnapshot, {
        method: "POST",
        requestSchema: ConnectRequest,
        body: { guild_id: guildId, channel_id: channelId },
        silent,
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
