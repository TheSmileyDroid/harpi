
  import { z } from "zod";

// <Schemas>
export type Authenticated = z.infer<typeof Authenticated>;
export const Authenticated = z.strictObject({ authenticated: z.boolean() });

export type BotStatus = z.infer<typeof BotStatus>;
export const BotStatus = z.strictObject({ online: z.boolean() });

export type Channel = z.infer<typeof Channel>;
export const Channel = z.strictObject({ id: z.string(), name: z.string() });

export type ChannelList = z.infer<typeof ChannelList>;
export const ChannelList = z.strictObject({ channels: z.array(Channel) });

export type ConnectRequest = z.infer<typeof ConnectRequest>;
export const ConnectRequest = z.strictObject({ channel_id: z.string().nullable().default(null), guild_id: z.string().nullable().default(null) }).partial();

export type Connection = z.infer<typeof Connection>;
export const Connection = z.strictObject({ channel_id: z.string().nullable(), connected: z.boolean() });

export type ErrorDetail = z.infer<typeof ErrorDetail>;
export const ErrorDetail = z.strictObject({ code: z.string(), message: z.string() });

export type ErrorEnvelope = z.infer<typeof ErrorEnvelope>;
export const ErrorEnvelope = z.strictObject({ error: ErrorDetail });

export type Guild = z.infer<typeof Guild>;
export const Guild = z.strictObject({ id: z.string(), name: z.string() });

export type GuildList = z.infer<typeof GuildList>;
export const GuildList = z.strictObject({ guilds: z.array(Guild) });

export type Layer = z.infer<typeof Layer>;
export const Layer = z.strictObject({ id: z.string(), thumbnail: z.string(), title: z.string(), url: z.string(), volume: z.number() });

export type LayerIdRequest = z.infer<typeof LayerIdRequest>;
export const LayerIdRequest = z.strictObject({ layer_id: z.string().nullable().default(null) }).partial();

export type LayerVolumeRequest = z.infer<typeof LayerVolumeRequest>;
export const LayerVolumeRequest = z.strictObject({ layer_id: z.string().nullable().default(null), volume: z.number().nullable().default(null) }).partial();

export type LoopRequest = z.infer<typeof LoopRequest>;
export const LoopRequest = z.strictObject({ mode: z.string().nullable().default(null) }).partial();

export type Track = z.infer<typeof Track>;
export const Track = z.strictObject({ duration: z.number().int(), thumbnail: z.string(), title: z.string(), uploader: z.string(), url: z.string() });

export type PlaybackStatus = z.infer<typeof PlaybackStatus>;
export const PlaybackStatus = z.strictObject({ channel_id: z.string().nullable(), connected: z.boolean(), current_music: Track.nullable(), guild_id: z.string().nullable(), is_paused: z.boolean(), is_playing: z.boolean(), layers: z.array(Layer), loop_mode: z.string(), progress: z.number(), queue: z.array(Track), volume: z.number() });

export type ReloadEvent = z.infer<typeof ReloadEvent>;
export const ReloadEvent = z.strictObject({ scope: z.string() });

export type SearchRequest = z.infer<typeof SearchRequest>;
export const SearchRequest = z.strictObject({ term: z.string().nullable().default(null) }).partial();

export type SearchResults = z.infer<typeof SearchResults>;
export const SearchResults = z.strictObject({ results: z.array(Track) });

export type SeekRequest = z.infer<typeof SeekRequest>;
export const SeekRequest = z.strictObject({ position: z.number().nullable().default(null) }).partial();

export type SessionRequest = z.infer<typeof SessionRequest>;
export const SessionRequest = z.strictObject({ token: z.string().nullable().default(null) }).partial();

export type StatusSnapshot = z.infer<typeof StatusSnapshot>;
export const StatusSnapshot = z.strictObject({ bot: BotStatus, connection: Connection, guild_id: z.string().nullable(), playback: PlaybackStatus.nullable() });

export type SseEnvelope = z.infer<typeof SseEnvelope>;
export const SseEnvelope = z.union([StatusSnapshot, ReloadEvent]);

export type UrlRequest = z.infer<typeof UrlRequest>;
export const UrlRequest = z.strictObject({ url: z.string().nullable().default(null) }).partial();

export type VolumeRequest = z.infer<typeof VolumeRequest>;
export const VolumeRequest = z.strictObject({ volume: z.number().nullable().default(null) }).partial();

// </Schemas>

  
  
  