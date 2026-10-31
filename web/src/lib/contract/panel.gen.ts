
  import { z } from "zod";

// <Schemas>
export type Authenticated = z.infer<typeof Authenticated>;
export const Authenticated = z.strictObject({ authenticated: z.boolean() });

export type BotStatus = z.infer<typeof BotStatus>;
export const BotStatus = z.strictObject({ online: z.boolean() });

export type OpenTable = z.infer<typeof OpenTable>;
export const OpenTable = z.strictObject({ channel_id: z.string(), id: z.string(), name: z.string() });

export type CampaignDetail = z.infer<typeof CampaignDetail>;
export const CampaignDetail = z.strictObject({ config_error: z.string().nullable().default(null), name: z.string(), open_table: OpenTable.nullable(), role: z.enum(["narrator", "player", "pending"]), slug: z.string(), system: z.string() });

export type CampaignSummary = z.infer<typeof CampaignSummary>;
export const CampaignSummary = z.strictObject({ name: z.string(), role: z.enum(["narrator", "player", "pending"]), slug: z.string(), system: z.string() });

export type CampaignList = z.infer<typeof CampaignList>;
export const CampaignList = z.strictObject({ campaigns: z.array(CampaignSummary) });

export type Channel = z.infer<typeof Channel>;
export const Channel = z.strictObject({ id: z.string(), name: z.string() });

export type ChannelList = z.infer<typeof ChannelList>;
export const ChannelList = z.strictObject({ channels: z.array(Channel) });

export type CharacterCard = z.infer<typeof CharacterCard>;
export const CharacterCard = z.strictObject({ concept: z.string().nullable(), id: z.string(), name: z.string(), portrait: z.string().nullable(), summary: z.string().nullable() });

export type SheetAspect = z.infer<typeof SheetAspect>;
export const SheetAspect = z.strictObject({ label: z.string(), text: z.string() });

export type SheetConsequence = z.infer<typeof SheetConsequence>;
export const SheetConsequence = z.strictObject({ severity: z.string(), text: z.string(), value: z.number().int() });

export type SheetExtra = z.infer<typeof SheetExtra>;
export const SheetExtra = z.strictObject({ cost: z.number().int().nullable(), kind: z.string(), name: z.string(), text: z.string() });

export type SheetInventoryEntry = z.infer<typeof SheetInventoryEntry>;
export const SheetInventoryEntry = z.strictObject({ item: z.string(), note: z.string(), qty: z.number().int() });

export type SheetLadderStep = z.infer<typeof SheetLadderStep>;
export const SheetLadderStep = z.strictObject({ label: z.string(), rank: z.number().int() });

export type SheetSkill = z.infer<typeof SheetSkill>;
export const SheetSkill = z.strictObject({ label: z.string(), name: z.string(), rank: z.number().int() });

export type SheetStressBox = z.infer<typeof SheetStressBox>;
export const SheetStressBox = z.strictObject({ checked: z.boolean(), value: z.number().int() });

export type SheetStressTrack = z.infer<typeof SheetStressTrack>;
export const SheetStressTrack = z.strictObject({ boxes: z.array(SheetStressBox), track: z.string() });

export type SheetStunt = z.infer<typeof SheetStunt>;
export const SheetStunt = z.strictObject({ name: z.string(), refresh_cost: z.number().int(), text: z.string() });

export type SheetDetail = z.infer<typeof SheetDetail>;
export const SheetDetail = z.strictObject({ aspects: z.array(SheetAspect), character_id: z.string().nullable(), consequences: z.array(SheetConsequence), error: z.string().nullable(), extras: z.array(SheetExtra), fate_points: z.number().int().nullable(), id: z.string(), inventory: z.array(SheetInventoryEntry), ladder: z.array(SheetLadderStep), owner: z.string().nullable(), read_only: z.boolean(), refresh: z.number().int().nullable(), skills: z.array(SheetSkill), state: z.enum(["ok", "invalid"]), status: z.enum(["active", "pending", "archived"]), stress: z.array(SheetStressTrack), stunts: z.array(SheetStunt) });

export type CharacterDetail = z.infer<typeof CharacterDetail>;
export const CharacterDetail = z.strictObject({ card: CharacterCard, kind: z.enum(["sheet", "card"]), sheet: SheetDetail.nullable() });

export type CharacterList = z.infer<typeof CharacterList>;
export const CharacterList = z.strictObject({ characters: z.array(CharacterCard) });

export type ConnectRequest = z.infer<typeof ConnectRequest>;
export const ConnectRequest = z.strictObject({ channel_id: z.string().nullable().default(null), guild_id: z.string().nullable().default(null) }).partial();

export type Connection = z.infer<typeof Connection>;
export const Connection = z.strictObject({ channel_id: z.string().nullable(), connected: z.boolean() });

export type ConnectionEvent = z.infer<typeof ConnectionEvent>;
export const ConnectionEvent = z.strictObject({ action: z.string(), actor_id: z.string().nullable(), actor_name: z.string().nullable(), at: z.number().int(), channel_id: z.string().nullable(), channel_name: z.string().nullable() });

export type Guild = z.infer<typeof Guild>;
export const Guild = z.strictObject({ id: z.string(), name: z.string() });

export type Directory = z.infer<typeof Directory>;
export const Directory = z.strictObject({ channels: z.array(Channel), guild_id: z.string().nullable(), guilds: z.array(Guild) });

export type ErrorDetail = z.infer<typeof ErrorDetail>;
export const ErrorDetail = z.strictObject({ code: z.string(), message: z.string() });

export type ErrorEnvelope = z.infer<typeof ErrorEnvelope>;
export const ErrorEnvelope = z.strictObject({ error: ErrorDetail });

export type GuildList = z.infer<typeof GuildList>;
export const GuildList = z.strictObject({ guilds: z.array(Guild) });

export type Heartbeat = z.infer<typeof Heartbeat>;
export const Heartbeat = z.strictObject({  }).partial();

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

export type Position = z.infer<typeof Position>;
export const Position = z.strictObject({ progress: z.number() });

export type Viewer = z.infer<typeof Viewer>;
export const Viewer = z.strictObject({ channel_id: z.string().nullable(), channel_name: z.string().nullable(), display_name: z.string().nullable(), seen_at: z.number().int(), user_id: z.string(), username: z.string() });

export type Presence = z.infer<typeof Presence>;
export const Presence = z.strictObject({ guild_id: z.string().nullable(), last_connection: ConnectionEvent.nullable(), viewers: z.array(Viewer) });

export type ReloadEvent = z.infer<typeof ReloadEvent>;
export const ReloadEvent = z.strictObject({ scope: z.string() });

export type SearchRequest = z.infer<typeof SearchRequest>;
export const SearchRequest = z.strictObject({ term: z.string().nullable().default(null) }).partial();

export type SearchResults = z.infer<typeof SearchResults>;
export const SearchResults = z.strictObject({ results: z.array(Track) });

export type SeekRequest = z.infer<typeof SeekRequest>;
export const SeekRequest = z.strictObject({ position: z.number().nullable().default(null) }).partial();

export type StatusSnapshot = z.infer<typeof StatusSnapshot>;
export const StatusSnapshot = z.strictObject({ bot: BotStatus, connection: Connection, guild_id: z.string().nullable(), playback: PlaybackStatus.nullable() });

export type SseEnvelope = z.infer<typeof SseEnvelope>;
export const SseEnvelope = z.union([StatusSnapshot, ReloadEvent, Presence, Position, Heartbeat, Directory]);

export type UrlRequest = z.infer<typeof UrlRequest>;
export const UrlRequest = z.strictObject({ url: z.string().nullable().default(null) }).partial();

export type VolumeRequest = z.infer<typeof VolumeRequest>;
export const VolumeRequest = z.strictObject({ volume: z.number().nullable().default(null) }).partial();

// </Schemas>

  
  
  