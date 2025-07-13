/* eslint-disable */
/* tslint:disable */
// @ts-nocheck
/*
 * ---------------------------------------------------------------
 * ## THIS FILE WAS GENERATED VIA SWAGGER-TYPESCRIPT-API        ##
 * ##                                                           ##
 * ## AUTHOR: acacode                                           ##
 * ## SOURCE: https://github.com/acacode/swagger-typescript-api ##
 * ---------------------------------------------------------------
 */

/**
 * LoopMode
 * Enum que representa o modo de loop.
 */
export enum LoopMode {
  Value0 = 0,
  Value1 = 1,
  Value2 = 2,
}

/**
 * CanvasData
 * Dados do canvas para uma guilda.
 */
export interface CanvasData {
  /** Elements */
  elements?: Record<string, any>[];
  /** App State */
  app_state?: Record<string, any> | null;
}

/**
 * CogInfo
 * Information about a Discord cog.
 */
export interface CogInfo {
  /**
   * Name
   * Cog name
   */
  name: string;
  /**
   * Description
   * Cog description
   */
  description?: string | null;
  /**
   * Enabled
   * Whether the cog is enabled
   * @default true
   */
  enabled?: boolean;
  /**
   * Commands
   * Commands in this cog
   */
  commands?: CommandInfo[];
  /**
   * Usage Stats
   * Usage statistics
   */
  usage_stats?: CommandUsage[];
}

/**
 * CogStatusUpdate
 * Request model for updating cog status.
 */
export interface CogStatusUpdate {
  /**
   * Enabled
   * Whether to enable or disable the cog
   */
  enabled: boolean;
}

/**
 * CommandInfo
 * Information about a Discord command.
 */
export interface CommandInfo {
  /**
   * Name
   * Command name
   */
  name: string;
  /**
   * Description
   * Command description
   */
  description?: string | null;
  /**
   * Aliases
   * Command aliases
   */
  aliases?: string[];
  /**
   * Usage
   * Command usage example
   */
  usage?: string | null;
}

/**
 * CommandUsage
 * Usage statistics for a command.
 */
export interface CommandUsage {
  /**
   * Command Name
   * Command name
   */
  command_name: string;
  /**
   * Total Uses
   * Total number of uses
   * @default 0
   */
  total_uses?: number;
  /**
   * Last Used
   * Last time used
   */
  last_used?: string | null;
  /**
   * Last User
   * Last user who used it
   */
  last_user?: string | null;
}

/**
 * CommandUsageUpdate
 * Request model for updating command usage.
 */
export interface CommandUsageUpdate {
  /**
   * Command Name
   * Command name
   */
  command_name: string;
  /**
   * User Id
   * User who used the command
   */
  user_id?: string | null;
}

/**
 * DiskInfo
 * Informações de um disco.
 */
export interface DiskInfo {
  /** Path */
  path: string;
  /** Total */
  total: number;
  /** Used */
  used: number;
  /** Free */
  free: number;
  /** Percent */
  percent: number;
}

/** HTTPValidationError */
export interface HTTPValidationError {
  /** Detail */
  detail?: ValidationError[];
}

/**
 * IGuild
 * Guild model.
 */
export interface IGuild {
  /** Id */
  id: string;
  /** Name */
  name: string;
  /** Description */
  description: string | null;
  /** Approximate Member Count */
  approximate_member_count: number;
  /** Icon */
  icon: string | null;
  /** Voice Channels */
  voice_channels: IVoiceChannel[] | null;
  /** Text Channels */
  text_channels: ITextChannel[] | null;
}

/**
 * ILoopRequest
 * Request to toggle loop
 */
export interface ILoopRequest {
  /** Enum que representa o modo de loop. */
  mode: LoopMode;
}

/**
 * IMusic
 * Music data model.
 */
export interface IMusic {
  /** Title */
  title: string;
  /** Url */
  url: string;
  /** Thumbnail */
  thumbnail: string | null;
  /** Duration */
  duration: number;
  /** Artists */
  artists: string[] | null;
  /** Album */
  album: string | null;
  /** Categories */
  categories: string[];
  /** Release Year */
  release_year: number | null;
}

/**
 * IMusicState
 * Model for sending all the Music state of a guild.
 */
export interface IMusicState {
  /** Queue */
  queue: IMusic[];
  /** Enum que representa o modo de loop. */
  loop_mode: LoopMode;
  /** Progress */
  progress: number;
  current_voice_channel: IVoiceChannel | null;
  /**
   * Paused
   * @default false
   */
  paused?: boolean;
  /**
   * Playing
   * @default false
   */
  playing?: boolean;
}

/**
 * IStatus
 * Estado atual do Bot.
 */
export interface IStatus {
  /** Status */
  status: "online" | "offline";
}

/**
 * ITextChannel
 * Text channel model.
 */
export interface ITextChannel {
  /** Id */
  id: string;
  /** Name */
  name: string;
}

/**
 * IVoiceChannel
 * Voice channel model.
 */
export interface IVoiceChannel {
  /** Id */
  id: string;
  /** Name */
  name: string;
  /** Members */
  members: string[];
}

/**
 * MinecraftPlayer
 * Informações de um jogador de Minecraft.
 */
export interface MinecraftPlayer {
  /** Name */
  name: string;
  /** Id */
  id?: string | null;
}

/**
 * MinecraftStatus
 * Status do servidor Minecraft.
 */
export interface MinecraftStatus {
  /**
   * Is Running
   * Se o servidor está rodando
   */
  is_running: boolean;
  /** Version */
  version?: string | null;
  /** Online Players */
  online_players?: number | null;
  /** Max Players */
  max_players?: number | null;
  /**
   * Players List
   * @default []
   */
  players_list?: MinecraftPlayer[];
  /** Cpu Percent */
  cpu_percent?: number | null;
  /** Memory Mb */
  memory_mb?: number | null;
}

/**
 * ProcessInfo
 * Informações de um processo do sistema.
 */
export interface ProcessInfo {
  /** Pid */
  pid: number;
  /** Name */
  name: string;
  /** Cpu Percent */
  cpu_percent: number;
  /** Memory Percent */
  memory_percent: number;
  /** Command */
  command: string;
}

/**
 * SystemStatus
 * Status do sistema com informações de recursos.
 */
export interface SystemStatus {
  /**
   * Cpu Percent
   * Percentual de uso de CPU
   */
  cpu_percent: number;
  /**
   * Memory Percent
   * Percentual de uso de memória
   */
  memory_percent: number;
  /**
   * Memory Total
   * Total de memória em GB
   */
  memory_total: number;
  /**
   * Memory Used
   * Memória usada em GB
   */
  memory_used: number;
  /**
   * Uptime
   * Tempo de atividade do sistema
   */
  uptime: string;
  /**
   * Disks
   * Informações de discos
   */
  disks: DiskInfo[];
}

/**
 * TopProcesses
 * Lista dos processos mais ativos do sistema.
 */
export interface TopProcesses {
  /**
   * Timestamp
   * Timestamp da coleta
   */
  timestamp: string;
  /**
   * Processes
   * Lista de processos
   */
  processes: ProcessInfo[];
}

/** ValidationError */
export interface ValidationError {
  /** Location */
  loc: (string | number)[];
  /** Message */
  msg: string;
  /** Error Type */
  type: string;
}

import type {
  AxiosInstance,
  AxiosRequestConfig,
  AxiosResponse,
  HeadersDefaults,
  ResponseType,
} from "axios";
import axios from "axios";

export type QueryParamsType = Record<string | number, any>;

export interface FullRequestParams
  extends Omit<AxiosRequestConfig, "data" | "params" | "url" | "responseType"> {
  /** set parameter to `true` for call `securityWorker` for this request */
  secure?: boolean;
  /** request path */
  path: string;
  /** content type of request body */
  type?: ContentType;
  /** query params */
  query?: QueryParamsType;
  /** format of response (i.e. response.json() -> format: "json") */
  format?: ResponseType;
  /** request body */
  body?: unknown;
}

export type RequestParams = Omit<
  FullRequestParams,
  "body" | "method" | "query" | "path"
>;

export interface ApiConfig<SecurityDataType = unknown>
  extends Omit<AxiosRequestConfig, "data" | "cancelToken"> {
  securityWorker?: (
    securityData: SecurityDataType | null,
  ) => Promise<AxiosRequestConfig | void> | AxiosRequestConfig | void;
  secure?: boolean;
  format?: ResponseType;
}

export enum ContentType {
  Json = "application/json",
  JsonApi = "application/vnd.api+json",
  FormData = "multipart/form-data",
  UrlEncoded = "application/x-www-form-urlencoded",
  Text = "text/plain",
}

export class HttpClient<SecurityDataType = unknown> {
  public instance: AxiosInstance;
  private securityData: SecurityDataType | null = null;
  private securityWorker?: ApiConfig<SecurityDataType>["securityWorker"];
  private secure?: boolean;
  private format?: ResponseType;

  constructor({
    securityWorker,
    secure,
    format,
    ...axiosConfig
  }: ApiConfig<SecurityDataType> = {}) {
    this.instance = axios.create({
      ...axiosConfig,
      baseURL: axiosConfig.baseURL || "",
    });
    this.secure = secure;
    this.format = format;
    this.securityWorker = securityWorker;
  }

  public setSecurityData = (data: SecurityDataType | null) => {
    this.securityData = data;
  };

  protected mergeRequestParams(
    params1: AxiosRequestConfig,
    params2?: AxiosRequestConfig,
  ): AxiosRequestConfig {
    const method = params1.method || (params2 && params2.method);

    return {
      ...this.instance.defaults,
      ...params1,
      ...(params2 || {}),
      headers: {
        ...((method &&
          this.instance.defaults.headers[
            method.toLowerCase() as keyof HeadersDefaults
          ]) ||
          {}),
        ...(params1.headers || {}),
        ...((params2 && params2.headers) || {}),
      },
    };
  }

  protected stringifyFormItem(formItem: unknown) {
    if (typeof formItem === "object" && formItem !== null) {
      return JSON.stringify(formItem);
    } else {
      return `${formItem}`;
    }
  }

  protected createFormData(input: Record<string, unknown>): FormData {
    if (input instanceof FormData) {
      return input;
    }
    return Object.keys(input || {}).reduce((formData, key) => {
      const property = input[key];
      const propertyContent: any[] =
        property instanceof Array ? property : [property];

      for (const formItem of propertyContent) {
        const isFileType = formItem instanceof Blob || formItem instanceof File;
        formData.append(
          key,
          isFileType ? formItem : this.stringifyFormItem(formItem),
        );
      }

      return formData;
    }, new FormData());
  }

  public request = async <T = any, _E = any>({
    secure,
    path,
    type,
    query,
    format,
    body,
    ...params
  }: FullRequestParams): Promise<AxiosResponse<T>> => {
    const secureParams =
      ((typeof secure === "boolean" ? secure : this.secure) &&
        this.securityWorker &&
        (await this.securityWorker(this.securityData))) ||
      {};
    const requestParams = this.mergeRequestParams(params, secureParams);
    const responseFormat = format || this.format || undefined;

    if (
      type === ContentType.FormData &&
      body &&
      body !== null &&
      typeof body === "object"
    ) {
      body = this.createFormData(body as Record<string, unknown>);
    }

    if (
      type === ContentType.Text &&
      body &&
      body !== null &&
      typeof body !== "string"
    ) {
      body = JSON.stringify(body);
    }

    return this.instance.request({
      ...requestParams,
      headers: {
        ...(requestParams.headers || {}),
        ...(type ? { "Content-Type": type } : {}),
      },
      params: query,
      responseType: responseFormat,
      data: body,
      url: path,
    });
  };
}

/**
 * @title Harpi API
 * @version 1.0.0
 *
 * Discord bot management API
 */
export class Api<
  SecurityDataType extends unknown,
> extends HttpClient<SecurityDataType> {
  api = {
    /**
     * @description Retorna uma lista de guildas disponíveis. Returns ------- list[IGuild] As guildas.
     *
     * @tags guilds
     * @name GetApiGuildsGet
     * @summary Get
     * @request GET:/api/guilds
     */
    getApiGuildsGet: (params: RequestParams = {}) =>
      this.request<IGuild[], void>({
        path: `/api/guilds`,
        method: "GET",
        format: "json",
        ...params,
      }),

    /**
     * @description Retorna uma guilda a partir de um ID. Parameters ---------- request : Request _description_ idx : str ID da Guilda. Returns ------- IGuild _description_
     *
     * @tags guilds
     * @name GetGuildApiGuildsGet
     * @summary Get Guild
     * @request GET:/api/guilds/
     */
    getGuildApiGuildsGet: (
      query: {
        /** Idx */
        idx: string;
      },
      params: RequestParams = {},
    ) =>
      this.request<IGuild | null, void | HTTPValidationError>({
        path: `/api/guilds/`,
        method: "GET",
        query: query,
        format: "json",
        ...params,
      }),

    /**
     * @description Retorna a lista de músicas de uma Guilda (Incluindo a música atual). Parameters ---------- request : Request _description_ idx : str Guild ID. Returns ------- list[IMusic] _description_
     *
     * @tags guilds
     * @name GetMusicListApiGuildsMusicListGet
     * @summary Get Music List
     * @request GET:/api/guilds/music/list
     */
    getMusicListApiGuildsMusicListGet: (
      query: {
        /** Idx */
        idx: string;
      },
      params: RequestParams = {},
    ) =>
      this.request<IMusic[], void | HTTPValidationError>({
        path: `/api/guilds/music/list`,
        method: "GET",
        query: query,
        format: "json",
        ...params,
      }),

    /**
     * @description Get the current music state for a guild. Returns ------- IMusicState Complete music state.
     *
     * @tags guilds
     * @name GetMusicStateApiGuildsStateGet
     * @summary Get Music State
     * @request GET:/api/guilds/state
     */
    getMusicStateApiGuildsStateGet: (
      query: {
        /** Idx */
        idx: string;
      },
      params: RequestParams = {},
    ) =>
      this.request<IMusicState, void | HTTPValidationError>({
        path: `/api/guilds/state`,
        method: "GET",
        query: query,
        format: "json",
        ...params,
      }),

    /**
     * @description Add a song to the queue. Raises ------ HTTPException If the URL is empty.
     *
     * @tags guilds
     * @name AddToQueueApiGuildsQueuePost
     * @summary Add To Queue
     * @request POST:/api/guilds/queue
     */
    addToQueueApiGuildsQueuePost: (
      query: {
        /** Idx */
        idx: string;
        /** Url */
        url: string;
      },
      params: RequestParams = {},
    ) =>
      this.request<null, void | HTTPValidationError>({
        path: `/api/guilds/queue`,
        method: "POST",
        query: query,
        format: "json",
        ...params,
      }),

    /**
     * @description Obtém os dados do canvas para uma guilda específica. Parameters ---------- request : Request Requisição FastAPI idx : str ID da guilda Returns ------- CanvasData Dados do canvas da guilda
     *
     * @tags guilds
     * @name GetCanvasApiGuildsCanvasGet
     * @summary Get Canvas
     * @request GET:/api/guilds/canvas
     */
    getCanvasApiGuildsCanvasGet: (
      query: {
        /** Idx */
        idx: string;
      },
      params: RequestParams = {},
    ) =>
      this.request<CanvasData, void | HTTPValidationError>({
        path: `/api/guilds/canvas`,
        method: "GET",
        query: query,
        format: "json",
        ...params,
      }),

    /**
     * @description Skip the current music.
     *
     * @tags guilds
     * @name SkipMusicApiGuildsSkipPost
     * @summary Skip Music
     * @request POST:/api/guilds/skip
     */
    skipMusicApiGuildsSkipPost: (
      query: {
        /** Idx */
        idx: string;
      },
      params: RequestParams = {},
    ) =>
      this.request<null, void | HTTPValidationError>({
        path: `/api/guilds/skip`,
        method: "POST",
        query: query,
        format: "json",
        ...params,
      }),

    /**
     * @description Pause the current music.
     *
     * @tags guilds
     * @name PauseMusicApiGuildsPausePost
     * @summary Pause Music
     * @request POST:/api/guilds/pause
     */
    pauseMusicApiGuildsPausePost: (
      query: {
        /** Idx */
        idx: string;
      },
      params: RequestParams = {},
    ) =>
      this.request<null, void | HTTPValidationError>({
        path: `/api/guilds/pause`,
        method: "POST",
        query: query,
        format: "json",
        ...params,
      }),

    /**
     * @description Resume the current music.
     *
     * @tags guilds
     * @name ResumeMusicApiGuildsResumePost
     * @summary Resume Music
     * @request POST:/api/guilds/resume
     */
    resumeMusicApiGuildsResumePost: (
      query: {
        /** Idx */
        idx: string;
      },
      params: RequestParams = {},
    ) =>
      this.request<null, void | HTTPValidationError>({
        path: `/api/guilds/resume`,
        method: "POST",
        query: query,
        format: "json",
        ...params,
      }),

    /**
     * @description Stop the current music.
     *
     * @tags guilds
     * @name StopMusicApiGuildsStopPost
     * @summary Stop Music
     * @request POST:/api/guilds/stop
     */
    stopMusicApiGuildsStopPost: (
      query: {
        /** Idx */
        idx: string;
      },
      params: RequestParams = {},
    ) =>
      this.request<null, void | HTTPValidationError>({
        path: `/api/guilds/stop`,
        method: "POST",
        query: query,
        format: "json",
        ...params,
      }),

    /**
     * @description Alterna o modo de loop.
     *
     * @tags guilds
     * @name LoopMusicApiGuildsLoopPost
     * @summary Loop Music
     * @request POST:/api/guilds/loop
     */
    loopMusicApiGuildsLoopPost: (
      query: {
        /** Idx */
        idx: string;
      },
      data: ILoopRequest,
      params: RequestParams = {},
    ) =>
      this.request<null, void | HTTPValidationError>({
        path: `/api/guilds/loop`,
        method: "POST",
        query: query,
        body: data,
        type: ContentType.Json,
        format: "json",
        ...params,
      }),

    /**
     * @description Connect to a voice channel.
     *
     * @tags guilds
     * @name ConnectToVoiceApiGuildsVoiceConnectPost
     * @summary Connect To Voice
     * @request POST:/api/guilds/voice/connect
     */
    connectToVoiceApiGuildsVoiceConnectPost: (
      query: {
        /** Idx */
        idx: string;
        /** Channel Id */
        channel_id: string | number;
      },
      params: RequestParams = {},
    ) =>
      this.request<null, void | HTTPValidationError>({
        path: `/api/guilds/voice/connect`,
        method: "POST",
        query: query,
        format: "json",
        ...params,
      }),

    /**
     * @description Obtém o status atual do sistema. Retorna informações sobre CPU, memória, discos e uptime. Returns ------- SystemStatus Objeto contendo estatísticas do sistema.
     *
     * @tags system
     * @name GetSystemStatusApiSystemStatusGet
     * @summary Get System Status
     * @request GET:/api/system/status
     */
    getSystemStatusApiSystemStatusGet: (params: RequestParams = {}) =>
      this.request<SystemStatus, void>({
        path: `/api/system/status`,
        method: "GET",
        format: "json",
        ...params,
      }),

    /**
     * @description Obtém o status do servidor Minecraft. Verifica se o servidor está rodando e obtém informações como versão, jogadores online e uso de recursos. Returns ------- MinecraftStatus Status do servidor Minecraft.
     *
     * @tags system
     * @name GetMinecraftStatusApiSystemMinecraftGet
     * @summary Get Minecraft Status
     * @request GET:/api/system/minecraft
     */
    getMinecraftStatusApiSystemMinecraftGet: (params: RequestParams = {}) =>
      this.request<MinecraftStatus, void>({
        path: `/api/system/minecraft`,
        method: "GET",
        format: "json",
        ...params,
      }),

    /**
     * @description Obtém informações sobre os processos mais ativos do sistema. Similar ao comando 'top' do Linux, retorna uma lista dos processos que estão consumindo mais recursos. Returns ------- TopProcesses Lista dos processos mais ativos.
     *
     * @tags system
     * @name GetTopProcessesApiSystemTopGet
     * @summary Get Top Processes
     * @request GET:/api/system/top
     */
    getTopProcessesApiSystemTopGet: (params: RequestParams = {}) =>
      this.request<TopProcesses, void>({
        path: `/api/system/top`,
        method: "GET",
        format: "json",
        ...params,
      }),

    /**
     * @description Retorna uma imagem com a saída do comando 'top'. Gera uma imagem contendo a saída formatada do comando 'top', semelhante ao que é feito no comando do Discord. Returns ------- StreamingResponse Imagem PNG contendo a saída do 'top'.
     *
     * @tags system
     * @name GetTopImageApiSystemTopImageGet
     * @summary Get Top Image
     * @request GET:/api/system/top/image
     */
    getTopImageApiSystemTopImageGet: (params: RequestParams = {}) =>
      this.request<any, void>({
        path: `/api/system/top/image`,
        method: "GET",
        format: "json",
        ...params,
      }),

    /**
     * @description Get all available cogs with their configuration and status. Returns a dictionary mapping cog names to their configuration, including enabled status, commands, and usage statistics. Returns: Dict[str, CogInfo]: All cog configurations
     *
     * @tags cogs
     * @name GetAllCogsApiCogsGet
     * @summary Get All Cogs
     * @request GET:/api/cogs/
     */
    getAllCogsApiCogsGet: (params: RequestParams = {}) =>
      this.request<Record<string, CogInfo>, void>({
        path: `/api/cogs/`,
        method: "GET",
        format: "json",
        ...params,
      }),

    /**
     * @description Get configuration for a specific cog. Args: cog_name: Name of the cog to retrieve Returns: CogInfo: The cog configuration Raises: HTTPException: If cog is not found
     *
     * @tags cogs
     * @name GetCogApiCogsCogNameGet
     * @summary Get Cog
     * @request GET:/api/cogs/{cog_name}
     */
    getCogApiCogsCogNameGet: (cogName: string, params: RequestParams = {}) =>
      this.request<CogInfo, void | HTTPValidationError>({
        path: `/api/cogs/${cogName}`,
        method: "GET",
        format: "json",
        ...params,
      }),

    /**
     * @description Enable or disable a cog. Args: cog_name: Name of the cog to toggle status_update: New status for the cog request: FastAPI request object to access bot instance Returns: Dict[str, str]: Status message Raises: HTTPException: If cog is not found or operation fails
     *
     * @tags cogs
     * @name ToggleCogApiCogsCogNameTogglePost
     * @summary Toggle Cog
     * @request POST:/api/cogs/{cog_name}/toggle
     */
    toggleCogApiCogsCogNameTogglePost: (
      cogName: string,
      data: CogStatusUpdate,
      params: RequestParams = {},
    ) =>
      this.request<Record<string, string>, void | HTTPValidationError>({
        path: `/api/cogs/${cogName}/toggle`,
        method: "POST",
        body: data,
        type: ContentType.Json,
        format: "json",
        ...params,
      }),

    /**
     * @description Get all commands for a specific cog with their documentation. Args: cog_name: Name of the cog Returns: List[dict]: List of commands with their documentation Raises: HTTPException: If cog is not found
     *
     * @tags cogs
     * @name GetCogCommandsApiCogsCogNameCommandsGet
     * @summary Get Cog Commands
     * @request GET:/api/cogs/{cog_name}/commands
     */
    getCogCommandsApiCogsCogNameCommandsGet: (
      cogName: string,
      params: RequestParams = {},
    ) =>
      this.request<Record<string, any>[], void | HTTPValidationError>({
        path: `/api/cogs/${cogName}/commands`,
        method: "GET",
        format: "json",
        ...params,
      }),

    /**
     * @description Get usage statistics for all commands in a cog. Args: cog_name: Name of the cog Returns: List[CommandUsage]: Usage statistics for all commands Raises: HTTPException: If cog is not found
     *
     * @tags cogs
     * @name GetCogUsageApiCogsCogNameUsageGet
     * @summary Get Cog Usage
     * @request GET:/api/cogs/{cog_name}/usage
     */
    getCogUsageApiCogsCogNameUsageGet: (
      cogName: string,
      params: RequestParams = {},
    ) =>
      this.request<CommandUsage[], void | HTTPValidationError>({
        path: `/api/cogs/${cogName}/usage`,
        method: "GET",
        format: "json",
        ...params,
      }),

    /**
     * @description Record usage of a command (typically called by the bot). Args: cog_name: Name of the cog usage_update: Command usage information Returns: Dict[str, str]: Status message Raises: HTTPException: If cog is not found
     *
     * @tags cogs
     * @name RecordCommandUsageApiCogsCogNameUsagePost
     * @summary Record Command Usage
     * @request POST:/api/cogs/{cog_name}/usage
     */
    recordCommandUsageApiCogsCogNameUsagePost: (
      cogName: string,
      data: CommandUsageUpdate,
      params: RequestParams = {},
    ) =>
      this.request<Record<string, string>, void | HTTPValidationError>({
        path: `/api/cogs/${cogName}/usage`,
        method: "POST",
        body: data,
        type: ContentType.Json,
        format: "json",
        ...params,
      }),

    /**
     * @description Get usage statistics for a specific command. Args: cog_name: Name of the cog command_name: Name of the command Returns: List[CommandUsage]: Usage statistics for the command Raises: HTTPException: If cog or command is not found
     *
     * @tags cogs
     * @name GetCommandUsageApiCogsCogNameUsageCommandNameGet
     * @summary Get Command Usage
     * @request GET:/api/cogs/{cog_name}/usage/{command_name}
     */
    getCommandUsageApiCogsCogNameUsageCommandNameGet: (
      cogName: string,
      commandName: string,
      params: RequestParams = {},
    ) =>
      this.request<CommandUsage[], void | HTTPValidationError>({
        path: `/api/cogs/${cogName}/usage/${commandName}`,
        method: "GET",
        format: "json",
        ...params,
      }),

    /**
     * @description Check the bot's status via a FastAPI endpoint. Returns ------- IStatus Status.
     *
     * @tags api
     * @name BotStatusApiStatusGet
     * @summary Bot Status
     * @request GET:/api/status
     */
    botStatusApiStatusGet: (params: RequestParams = {}) =>
      this.request<IStatus, any>({
        path: `/api/status`,
        method: "GET",
        format: "json",
        ...params,
      }),
  };
  path = {
    /**
     * @description Redirect all other requests to the frontend. Args: path (str): The path to redirect.
     *
     * @name RedirectPathGet
     * @summary Redirect
     * @request GET:/{path}
     */
    redirectPathGet: (path: string, params: RequestParams = {}) =>
      this.request<any, HTTPValidationError>({
        path: `/${path}`,
        method: "GET",
        format: "json",
        ...params,
      }),
  };
}
