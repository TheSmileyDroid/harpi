/* eslint-disable */
/* tslint:disable */
/*
 * ---------------------------------------------------------------
 * ## THIS FILE WAS GENERATED VIA SWAGGER-TYPESCRIPT-API        ##
 * ##                                                           ##
 * ## AUTHOR: acacode                                           ##
 * ## SOURCE: https://github.com/acacode/swagger-typescript-api ##
 * ---------------------------------------------------------------
 */

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
 * LoopMode
 * Enum que representa o modo de loop.
 */
export enum LoopMode {
  Value0 = 0,
  Value1 = 1,
  Value2 = 2,
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

import type { AxiosInstance, AxiosRequestConfig, AxiosResponse, HeadersDefaults, ResponseType } from "axios";
import axios from "axios";

export type QueryParamsType = Record<string | number, any>;

export interface FullRequestParams extends Omit<AxiosRequestConfig, "data" | "params" | "url" | "responseType"> {
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

export type RequestParams = Omit<FullRequestParams, "body" | "method" | "query" | "path">;

export interface ApiConfig<SecurityDataType = unknown> extends Omit<AxiosRequestConfig, "data" | "cancelToken"> {
  securityWorker?: (
    securityData: SecurityDataType | null,
  ) => Promise<AxiosRequestConfig | void> | AxiosRequestConfig | void;
  secure?: boolean;
  format?: ResponseType;
}

export enum ContentType {
  Json = "application/json",
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

  constructor({ securityWorker, secure, format, ...axiosConfig }: ApiConfig<SecurityDataType> = {}) {
    this.instance = axios.create({ ...axiosConfig, baseURL: axiosConfig.baseURL || "" });
    this.secure = secure;
    this.format = format;
    this.securityWorker = securityWorker;
  }

  public setSecurityData = (data: SecurityDataType | null) => {
    this.securityData = data;
  };

  protected mergeRequestParams(params1: AxiosRequestConfig, params2?: AxiosRequestConfig): AxiosRequestConfig {
    const method = params1.method || (params2 && params2.method);

    return {
      ...this.instance.defaults,
      ...params1,
      ...(params2 || {}),
      headers: {
        ...((method && this.instance.defaults.headers[method.toLowerCase() as keyof HeadersDefaults]) || {}),
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
      const propertyContent: any[] = property instanceof Array ? property : [property];

      for (const formItem of propertyContent) {
        const isFileType = formItem instanceof Blob || formItem instanceof File;
        formData.append(key, isFileType ? formItem : this.stringifyFormItem(formItem));
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

    if (type === ContentType.FormData && body && body !== null && typeof body === "object") {
      body = this.createFormData(body as Record<string, unknown>);
    }

    if (type === ContentType.Text && body && body !== null && typeof body !== "string") {
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
 * @title FastAPI
 * @version 0.1.0
 */
export class Api<SecurityDataType extends unknown> extends HttpClient<SecurityDataType> {
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
}
