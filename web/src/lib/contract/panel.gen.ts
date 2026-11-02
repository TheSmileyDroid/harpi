
  import { z } from "zod";

// <Schemas>
export type ApprovalDecision = z.infer<typeof ApprovalDecision>;
export const ApprovalDecision = z.strictObject({ decision: z.enum(["approve", "reject"]), note: z.string().default("") });

export type ApprovalItem = z.infer<typeof ApprovalItem>;
export const ApprovalItem = z.strictObject({ character_id: z.string().nullable(), character_name: z.string(), id: z.string(), note: z.string(), owner: z.string().nullable(), owner_name: z.string().nullable(), requested_at: z.number().int(), sheet_id: z.string().nullable() });

export type ApprovalList = z.infer<typeof ApprovalList>;
export const ApprovalList = z.strictObject({ approvals: z.array(ApprovalItem) });

export type AssetDetail = z.infer<typeof AssetDetail>;
export const AssetDetail = z.strictObject({ content_type: z.string(), hash: z.string(), name: z.string(), new_file: z.boolean(), path: z.string(), size: z.number().int(), url: z.string() });

export type AssetUpload = z.infer<typeof AssetUpload>;
export const AssetUpload = z.strictObject({ file: z.custom<Blob>((v) => typeof Blob !== "undefined" && v instanceof Blob) });

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

export type CharacterCreate = z.infer<typeof CharacterCreate>;
export const CharacterCreate = z.strictObject({ concept: z.string().nullable().default(null), name: z.string(), sheet: z.boolean().nullable().default(null), summary: z.string().nullable().default(null) });

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
export const SheetDetail = z.strictObject({ aspects: z.array(SheetAspect), character_id: z.string().nullable(), consequences: z.array(SheetConsequence), error: z.string().nullable(), extras: z.array(SheetExtra), fate_points: z.number().int().nullable(), hash: z.string(), history: z.string(), id: z.string(), inventory: z.array(SheetInventoryEntry), ladder: z.array(SheetLadderStep), notes: z.string(), owner: z.string().nullable(), read_only: z.boolean(), refresh: z.number().int().nullable(), rev: z.number().int(), review_note: z.string().nullable(), skills: z.array(SheetSkill), state: z.enum(["ok", "conflict", "missing", "invalid"]), status: z.enum(["active", "pending", "archived"]), stress: z.array(SheetStressTrack), stunts: z.array(SheetStunt), warnings: z.array(z.string()) });

export type CharacterDetail = z.infer<typeof CharacterDetail>;
export const CharacterDetail = z.strictObject({ card: CharacterCard, kind: z.enum(["sheet", "card"]), sheet: SheetDetail.nullable() });

export type CharacterList = z.infer<typeof CharacterList>;
export const CharacterList = z.strictObject({ characters: z.array(CharacterCard), own_character_id: z.string().nullable().default(null) });

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

export type SceneGrid = z.infer<typeof SceneGrid>;
export const SceneGrid = z.strictObject({ cell_px: z.number().int().min(1).max(1024), offset_x: z.number().int(), offset_y: z.number().int(), visible: z.boolean() });

export type SceneRect = z.infer<typeof SceneRect>;
export const SceneRect = z.strictObject({ h: z.number().int().min(1), w: z.number().int().min(1), x: z.number().int().min(0), y: z.number().int().min(0) });

export type SceneZone = z.infer<typeof SceneZone>;
export const SceneZone = z.strictObject({ id: z.string().default(""), label: z.string(), rects: z.array(SceneRect).min(1), revealed: z.boolean().default(false) });

export type SceneCreate = z.infer<typeof SceneCreate>;
export const SceneCreate = z.strictObject({ fog_outside: z.boolean().default(false), grid: SceneGrid.nullable().default(null), image: z.string().nullable().default(null), image_height: z.number().int().min(1).max(20000).nullable().default(null), image_width: z.number().int().min(1).max(20000).nullable().default(null), name: z.string().min(1).max(120), source: z.enum(["image", "sketch"]), zones: z.array(SceneZone) });

export type SceneImage = z.infer<typeof SceneImage>;
export const SceneImage = z.strictObject({ height: z.number().int().min(1), path: z.string(), width: z.number().int().min(1) });

export type SceneDetail = z.infer<typeof SceneDetail>;
export const SceneDetail = z.strictObject({ fog_outside: z.boolean(), grid: SceneGrid, hash: z.string(), image: SceneImage, name: z.string().min(1).max(120), saved: z.boolean(), slug: z.string(), source: z.enum(["image", "sketch"]), zones: z.array(SceneZone) });

export type SceneSummary = z.infer<typeof SceneSummary>;
export const SceneSummary = z.strictObject({ grid: SceneGrid, height: z.number().int(), in_use: z.boolean(), name: z.string(), saved: z.boolean(), slug: z.string(), source: z.enum(["image", "sketch"]), thumbnail: z.string().nullable(), width: z.number().int(), zone_count: z.number().int(), zones: z.array(SceneZone) });

export type SceneList = z.infer<typeof SceneList>;
export const SceneList = z.strictObject({ scenes: z.array(SceneSummary) });

export type SceneSave = z.infer<typeof SceneSave>;
export const SceneSave = z.strictObject({ base_hash: z.string(), fog_outside: z.boolean(), grid: SceneGrid, name: z.string().min(1).max(120), zones: z.array(SceneZone) });

export type SearchRequest = z.infer<typeof SearchRequest>;
export const SearchRequest = z.strictObject({ term: z.string().nullable().default(null) }).partial();

export type SearchResults = z.infer<typeof SearchResults>;
export const SearchResults = z.strictObject({ results: z.array(Track) });

export type SeekRequest = z.infer<typeof SeekRequest>;
export const SeekRequest = z.strictObject({ position: z.number().nullable().default(null) }).partial();

export type SheetActionResult = z.infer<typeof SheetActionResult>;
export const SheetActionResult = z.strictObject({ action: z.enum(["restore", "forget"]), sheet_id: z.string() });

export type SheetAspectInput = z.infer<typeof SheetAspectInput>;
export const SheetAspectInput = z.strictObject({ label: z.string(), text: z.string().default("") });

export type SheetConflictDecision = z.infer<typeof SheetConflictDecision>;
export const SheetConflictDecision = z.strictObject({ decision: z.enum(["ours", "theirs", "both"]) });

export type SheetConflictField = z.infer<typeof SheetConflictField>;
export const SheetConflictField = z.strictObject({ allow_both: z.boolean(), base: z.string().nullable(), character_id: z.string().nullable(), field_path: z.string(), id: z.string(), ours: z.string().nullable(), sheet_id: z.string(), theirs: z.string().nullable() });

export type SheetConflictDetail = z.infer<typeof SheetConflictDetail>;
export const SheetConflictDetail = z.strictObject({ conflicts: z.array(SheetConflictField), error: ErrorDetail });

export type SheetConflictList = z.infer<typeof SheetConflictList>;
export const SheetConflictList = z.strictObject({ conflicts: z.array(SheetConflictField) });

export type SheetConsequenceInput = z.infer<typeof SheetConsequenceInput>;
export const SheetConsequenceInput = z.strictObject({ severity: z.string(), text: z.string().default("") });

export type SheetExtraInput = z.infer<typeof SheetExtraInput>;
export const SheetExtraInput = z.strictObject({ cost: z.number().int().nullable().default(null), kind: z.string(), name: z.string().default(""), text: z.string().default("") });

export type SheetInventoryInput = z.infer<typeof SheetInventoryInput>;
export const SheetInventoryInput = z.strictObject({ item: z.string(), note: z.string().default(""), qty: z.number().int().default(1) });

export type SheetNoticeItem = z.infer<typeof SheetNoticeItem>;
export const SheetNoticeItem = z.strictObject({ character_id: z.string().nullable(), fields: z.array(z.string()), id: z.string(), name: z.string(), sheet_id: z.string(), state: z.enum(["conflito", "ausente", "invalido", "desconhecido"]), title: z.string() });

export type SheetNoticeList = z.infer<typeof SheetNoticeList>;
export const SheetNoticeList = z.strictObject({ notices: z.array(SheetNoticeItem) });

export type SheetSkillInput = z.infer<typeof SheetSkillInput>;
export const SheetSkillInput = z.strictObject({ name: z.string(), rank: z.number().int() });

export type SheetStressBoxInput = z.infer<typeof SheetStressBoxInput>;
export const SheetStressBoxInput = z.strictObject({ checked: z.boolean().default(false), value: z.number().int() });

export type SheetStressTrackInput = z.infer<typeof SheetStressTrackInput>;
export const SheetStressTrackInput = z.strictObject({ boxes: z.array(SheetStressBoxInput).optional(), track: z.string() });

export type SheetStuntInput = z.infer<typeof SheetStuntInput>;
export const SheetStuntInput = z.strictObject({ name: z.string(), refresh_cost: z.number().int().default(0), text: z.string().default("") });

export type SheetPatch = z.infer<typeof SheetPatch>;
export const SheetPatch = z.strictObject({ aspects: z.array(SheetAspectInput).nullable().default(null), base_hash: z.string(), consequences: z.array(SheetConsequenceInput).nullable().default(null), extras: z.array(SheetExtraInput).nullable().default(null), fate_points: z.number().int().nullable().default(null), history: z.string().nullable().default(null), inventory: z.array(SheetInventoryInput).nullable().default(null), notes: z.string().nullable().default(null), refresh: z.number().int().nullable().default(null), skills: z.array(SheetSkillInput).nullable().default(null), status: z.enum(["active", "pending", "archived"]).nullable().default(null), stress: z.array(SheetStressTrackInput).nullable().default(null), stunts: z.array(SheetStuntInput).nullable().default(null) });

export type StatusSnapshot = z.infer<typeof StatusSnapshot>;
export const StatusSnapshot = z.strictObject({ bot: BotStatus, connection: Connection, guild_id: z.string().nullable(), playback: PlaybackStatus.nullable() });

export type SseEnvelope = z.infer<typeof SseEnvelope>;
export const SseEnvelope = z.union([StatusSnapshot, ReloadEvent, Presence, Position, Heartbeat, Directory]);

export type TableClosedEvent = z.infer<typeof TableClosedEvent>;
export const TableClosedEvent = z.strictObject({ reason: z.string() });

export type TableConflictDetail = z.infer<typeof TableConflictDetail>;
export const TableConflictDetail = z.strictObject({ error: ErrorDetail, table: OpenTable });

export type TableDragMarker = z.infer<typeof TableDragMarker>;
export const TableDragMarker = z.strictObject({ active: z.boolean(), actor: z.string(), token_id: z.string() });

export type TableTokenMove = z.infer<typeof TableTokenMove>;
export const TableTokenMove = z.strictObject({ token_id: z.string().min(1).max(64), x: z.number().min(0), y: z.number().min(0) });

export type TableMoves = z.infer<typeof TableMoves>;
export const TableMoves = z.strictObject({ drag_id: z.string().min(1).max(64), final: z.boolean().default(false), moves: z.array(TableTokenMove).min(1).max(64) });

export type TableMovesResult = z.infer<typeof TableMovesResult>;
export const TableMovesResult = z.strictObject({ stream_rev: z.number().int() });

export type TableOpen = z.infer<typeof TableOpen>;
export const TableOpen = z.strictObject({ campaign: z.string(), channel_id: z.string(), name: z.string().nullable().default(null), scene: z.string() });

export type TableParticipant = z.infer<typeof TableParticipant>;
export const TableParticipant = z.strictObject({ acted: z.boolean(), character_id: z.string().nullable(), label: z.string(), owner_id: z.string().nullable(), token_id: z.string() });

export type TablePresenceEntry = z.infer<typeof TablePresenceEntry>;
export const TablePresenceEntry = z.strictObject({ name: z.string(), role: z.enum(["narrator", "player", "pending", "spectator"]) });

export type TableRollDiceGroup = z.infer<typeof TableRollDiceGroup>;
export const TableRollDiceGroup = z.strictObject({ kept: z.array(z.boolean()).nullable(), notation: z.string(), total: z.number().int(), values: z.array(z.number().int()) });

export type TableRollDice = z.infer<typeof TableRollDice>;
export const TableRollDice = z.strictObject({ expression: z.string(), groups: z.array(TableRollDiceGroup), index: z.number().int(), of: z.number().int() });

export type TableRoll = z.infer<typeof TableRoll>;
export const TableRoll = z.strictObject({ actor_id: z.string().nullable(), actor_label: z.string(), created_at: z.number().int(), dice: TableRollDice, discord_message_id: z.string().nullable(), expression: z.string(), id: z.string(), scene_id: z.string().nullable(), scene_label: z.string(), source: z.enum(["panel", "discord"]), table_id: z.string(), text: z.string(), total: z.number().int(), turn_id: z.string().nullable() });

export type TableRollCreate = z.infer<typeof TableRollCreate>;
export const TableRollCreate = z.strictObject({ expression: z.string().min(1) });

export type TableRollList = z.infer<typeof TableRollList>;
export const TableRollList = z.strictObject({ rolls: z.array(TableRoll) });

export type TableScene = z.infer<typeof TableScene>;
export const TableScene = z.strictObject({ fog: z.array(SceneRect).default([]), fog_outside: z.boolean(), grid: SceneGrid, height: z.number().int(), id: z.string(), map_url: z.string(), name: z.string(), saved: z.boolean().default(true), slug: z.string(), source: z.enum(["image", "sketch"]), width: z.number().int(), zones: z.array(SceneZone) });

export type TableSceneChange = z.infer<typeof TableSceneChange>;
export const TableSceneChange = z.strictObject({ scene: z.string() });

export type TableSheetChanged = z.infer<typeof TableSheetChanged>;
export const TableSheetChanged = z.strictObject({ character_id: z.string().nullable(), rev: z.number().int(), sheet_id: z.string(), state: z.enum(["ok", "conflict", "missing", "invalid"]) });

export type TableSpectators = z.infer<typeof TableSpectators>;
export const TableSpectators = z.strictObject({ enabled: z.boolean() });

export type TableToken = z.infer<typeof TableToken>;
export const TableToken = z.strictObject({ character_id: z.string().nullable(), color: z.string(), h: z.number().int(), id: z.string(), label: z.string(), owner_id: z.string().nullable(), rev: z.number().int(), visible: z.boolean(), w: z.number().int(), x: z.number(), y: z.number() });

export type TableTurn = z.infer<typeof TableTurn>;
export const TableTurn = z.strictObject({ character_id: z.string().nullable(), id: z.string(), label: z.string(), owner_id: z.string().nullable(), round: z.number().int(), started_at: z.number().int(), token_id: z.string().nullable() });

export type TableSummary = z.infer<typeof TableSummary>;
export const TableSummary = z.strictObject({ campaign: z.string(), channel_id: z.string(), id: z.string(), name: z.string(), participants: z.array(TableParticipant).default([]), role: z.enum(["narrator", "player", "pending", "spectator"]), round: z.number().int(), scene: TableScene.nullable(), spectators: z.boolean(), status: z.enum(["open", "closed"]), tokens: z.array(TableToken), turn: TableTurn.nullable().default(null), viewer_id: z.string(), warning: z.string().nullable().default(null) });

export type TableStreamSnapshot = z.infer<typeof TableStreamSnapshot>;
export const TableStreamSnapshot = z.strictObject({ drags: z.array(TableDragMarker), state: TableSummary, stream_rev: z.number().int(), table_id: z.string(), viewers: z.array(TablePresenceEntry) });

export type TableStreamDelta = z.infer<typeof TableStreamDelta>;
export const TableStreamDelta = z.strictObject({ from_stream_rev: z.number().int(), participants: z.array(TableParticipant), removed: z.array(z.string()), round: z.number().int(), scene: TableScene.nullable().default(null), scene_id: z.string().nullable(), spectators: z.boolean(), status: z.enum(["open", "closed"]), stream_rev: z.number().int(), tokens: z.array(TableToken), turn: TableTurn.nullable() });

export type TableStreamViewers = z.infer<typeof TableStreamViewers>;
export const TableStreamViewers = z.strictObject({ viewers: z.array(TablePresenceEntry) });

export type TableSseEnvelope = z.infer<typeof TableSseEnvelope>;
export const TableSseEnvelope = z.union([TableStreamSnapshot, TableStreamDelta, TableStreamViewers, TableDragMarker, TableSheetChanged, TableRoll, Heartbeat, TableClosedEvent]);

export type TableTokenCreate = z.infer<typeof TableTokenCreate>;
export const TableTokenCreate = z.strictObject({ character_id: z.string().nullable().default(null), color: z.string().default("#e9dfc7"), h: z.number().int().min(1).default(1), label: z.string(), owner_id: z.string().nullable().default(null), visible: z.boolean().default(true), w: z.number().int().min(1).default(1), x: z.number().min(0), y: z.number().min(0) });

export type TableTokenPatch = z.infer<typeof TableTokenPatch>;
export const TableTokenPatch = z.strictObject({ character_id: z.string().nullable().default(null), color: z.string().nullable().default(null), h: z.number().int().min(1).nullable().default(null), label: z.string().nullable().default(null), owner_id: z.string().nullable().default(null), visible: z.boolean().nullable().default(null), w: z.number().int().min(1).nullable().default(null), x: z.number().min(0).nullable().default(null), y: z.number().min(0).nullable().default(null) }).partial();

export type TableTurnRequest = z.infer<typeof TableTurnRequest>;
export const TableTurnRequest = z.strictObject({ action: z.enum(["open", "pass", "end"]), expected_turn_id: z.string().nullable().default(null), token_id: z.string().nullable().default(null) });

export type UrlRequest = z.infer<typeof UrlRequest>;
export const UrlRequest = z.strictObject({ url: z.string().nullable().default(null) }).partial();

export type VolumeRequest = z.infer<typeof VolumeRequest>;
export const VolumeRequest = z.strictObject({ volume: z.number().nullable().default(null) }).partial();

// </Schemas>

  
  
  