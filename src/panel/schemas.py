from __future__ import annotations

import math
import re
from typing import Annotated, Any, Literal

from pydantic import (
    BaseModel,
    BeforeValidator,
    ConfigDict,
    Field,
    RootModel,
)


def _as_snowflake(value: Any) -> str:
    if isinstance(value, bool):
        raise ValueError("a snowflake is never a boolean")
    if isinstance(value, int):
        return str(value)
    if isinstance(value, str):
        text = value.strip()
        if text.isascii() and text.isdigit():
            return str(int(text))
    raise ValueError("not a snowflake")


def _optional_snowflake(value: Any) -> str | None:
    if value is None:
        return None
    try:
        return _as_snowflake(value)
    except ValueError:
        return None


def _clean_text(value: Any) -> str | None:
    if isinstance(value, str) and value.strip():
        return value.strip()
    return None


def _finite_number(value: Any) -> float | None:
    if isinstance(value, bool) or not isinstance(value, int | float):
        return None
    number = float(value)
    return number if math.isfinite(number) else None


def _clean_scene_name(value: Any) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError("a scene needs a name")
    return value.strip()


TOKEN_COLOR = re.compile(r"^#[0-9a-f]{6}$")


def _token_color(value: Any) -> str:
    if (
        not isinstance(value, str)
        or TOKEN_COLOR.fullmatch(value.casefold()) is None
    ):
        raise ValueError("a token color is #rrggbb")
    return value.casefold()


def _clean_label(value: Any) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError("a token needs a label")
    label = value.strip()
    if len(label) > 120:
        raise ValueError("a token label is at most 120 characters")
    return label


Snowflake = Annotated[str, BeforeValidator(_as_snowflake)]
SnowflakeInput = Annotated[str | None, BeforeValidator(_optional_snowflake)]
TextInput = Annotated[str | None, BeforeValidator(_clean_text)]
NumberInput = Annotated[float | None, BeforeValidator(_finite_number)]
SceneName = Annotated[
    str,
    BeforeValidator(_clean_scene_name),
    Field(min_length=1, max_length=120),
]


class _Response(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Track(_Response):
    title: str
    url: str
    uploader: str
    duration: int
    thumbnail: str


class Layer(_Response):
    id: str
    title: str
    url: str
    volume: float
    thumbnail: str


class PlaybackStatus(_Response):
    guild_id: Snowflake | None
    connected: bool
    is_playing: bool
    is_paused: bool
    current_music: Track | None
    queue: list[Track]
    layers: list[Layer]
    loop_mode: str
    volume: float
    progress: float
    channel_id: Snowflake | None


class BotStatus(_Response):
    online: bool


class Connection(_Response):
    connected: bool
    channel_id: Snowflake | None


class Viewer(_Response):
    user_id: Snowflake
    username: str
    display_name: str | None
    channel_id: Snowflake | None
    channel_name: str | None
    seen_at: int


class ConnectionEvent(_Response):
    action: str
    channel_id: Snowflake | None
    channel_name: str | None
    actor_id: Snowflake | None
    actor_name: str | None
    at: int


class Presence(_Response):
    guild_id: Snowflake | None
    viewers: list[Viewer]
    last_connection: ConnectionEvent | None


class StatusSnapshot(_Response):
    bot: BotStatus
    guild_id: Snowflake | None
    connection: Connection
    playback: PlaybackStatus | None


class Position(_Response):
    progress: float


class Heartbeat(_Response):
    """An empty named frame; arriving at all is what proves the stream alive."""


class Directory(_Response):
    guild_id: Snowflake | None
    guilds: list[Guild]
    channels: list[Channel]


class Authenticated(_Response):
    authenticated: bool


class Guild(_Response):
    id: Snowflake
    name: str


class Channel(_Response):
    id: Snowflake
    name: str


class GuildList(_Response):
    guilds: list[Guild]


class ChannelList(_Response):
    channels: list[Channel]


CampaignRole = Literal["narrator", "player", "pending"]


class OpenTable(_Response):
    id: str
    name: str
    channel_id: Snowflake


class CampaignSummary(_Response):
    slug: str
    name: str
    system: str
    role: CampaignRole


class CampaignDetail(CampaignSummary):
    open_table: OpenTable | None
    config_error: str | None = None


class CampaignList(_Response):
    campaigns: list[CampaignSummary]


class CharacterCard(_Response):
    id: str
    name: str
    concept: str | None
    summary: str | None
    portrait: str | None


class CharacterList(_Response):
    characters: list[CharacterCard]
    own_character_id: str | None = None


class AssetDetail(_Response):
    name: str
    path: str
    url: str
    hash: str
    size: int
    content_type: str
    new_file: bool


class AssetUpload(BaseModel):
    file: bytes


SceneSource = Literal["image", "sketch"]


class SceneGrid(_Response):
    cell_px: int = Field(ge=1, le=1024)
    offset_x: int
    offset_y: int
    visible: bool


class SceneRect(_Response):
    x: int = Field(ge=0)
    y: int = Field(ge=0)
    w: int = Field(ge=1)
    h: int = Field(ge=1)


class SceneZone(_Response):
    id: str = ""
    label: str
    revealed: bool = False
    rects: list[SceneRect] = Field(min_length=1)


class SceneImage(_Response):
    path: str
    width: int = Field(ge=1)
    height: int = Field(ge=1)


class SceneBlueprint(_Response):
    slug: str
    name: SceneName
    source: SceneSource
    image: SceneImage
    grid: SceneGrid
    fog_outside: bool
    zones: list[SceneZone]


class SceneSummary(_Response):
    slug: str
    name: str
    source: SceneSource
    thumbnail: str | None
    width: int
    height: int
    grid: SceneGrid
    zones: list[SceneZone]
    zone_count: int
    saved: bool
    in_use: bool


class SceneList(_Response):
    scenes: list[SceneSummary]


class SceneDetail(SceneBlueprint):
    hash: str
    saved: bool


class SceneCreate(BaseModel):
    name: SceneName
    source: SceneSource
    image: TextInput = None
    image_width: int | None = Field(default=None, ge=1, le=20_000)
    image_height: int | None = Field(default=None, ge=1, le=20_000)
    grid: SceneGrid | None = None
    fog_outside: bool = False
    zones: list[SceneZone]


class SceneSave(BaseModel):
    base_hash: str
    name: SceneName
    grid: SceneGrid
    fog_outside: bool
    zones: list[SceneZone]


SheetStatus = Literal["active", "pending", "archived"]
SheetReadState = Literal["ok", "conflict", "missing", "invalid"]


class SheetLadderStep(_Response):
    rank: int
    label: str


class SheetAspect(_Response):
    label: str
    text: str


class SheetSkill(_Response):
    name: str
    rank: int
    label: str


class SheetStunt(_Response):
    name: str
    text: str
    refresh_cost: int


class SheetStressBox(_Response):
    value: int
    checked: bool


class SheetStressTrack(_Response):
    track: str
    boxes: list[SheetStressBox]


class SheetConsequence(_Response):
    severity: str
    value: int
    text: str


class SheetExtra(_Response):
    kind: str
    name: str
    text: str
    cost: int | None


class SheetInventoryEntry(_Response):
    item: str
    qty: int
    note: str


class SheetDetail(_Response):
    id: str
    character_id: str | None
    owner: SnowflakeInput
    status: SheetStatus
    state: SheetReadState
    read_only: bool
    error: str | None
    hash: str
    rev: int
    history: str
    notes: str
    review_note: str | None
    warnings: list[str]
    refresh: int | None
    fate_points: int | None
    ladder: list[SheetLadderStep]
    aspects: list[SheetAspect]
    skills: list[SheetSkill]
    stunts: list[SheetStunt]
    stress: list[SheetStressTrack]
    consequences: list[SheetConsequence]
    extras: list[SheetExtra]
    inventory: list[SheetInventoryEntry]


class SheetAspectInput(BaseModel):
    label: str
    text: str = ""


class SheetSkillInput(BaseModel):
    name: str
    rank: int


class SheetStuntInput(BaseModel):
    name: str
    text: str = ""
    refresh_cost: int = 0


class SheetStressBoxInput(BaseModel):
    value: int
    checked: bool = False


class SheetStressTrackInput(BaseModel):
    track: str
    boxes: list[SheetStressBoxInput] = Field(default_factory=list)


class SheetConsequenceInput(BaseModel):
    severity: str
    text: str = ""


class SheetExtraInput(BaseModel):
    kind: str
    name: str = ""
    text: str = ""
    cost: int | None = None


class SheetInventoryInput(BaseModel):
    item: str
    qty: int = 1
    note: str = ""


class SheetPatch(BaseModel):
    base_hash: str
    status: SheetStatus | None = None
    refresh: int | None = None
    fate_points: int | None = None
    aspects: list[SheetAspectInput] | None = None
    skills: list[SheetSkillInput] | None = None
    stunts: list[SheetStuntInput] | None = None
    stress: list[SheetStressTrackInput] | None = None
    consequences: list[SheetConsequenceInput] | None = None
    extras: list[SheetExtraInput] | None = None
    inventory: list[SheetInventoryInput] | None = None
    history: str | None = None
    notes: str | None = None


class CharacterDetail(_Response):
    kind: Literal["sheet", "card"]
    card: CharacterCard
    sheet: SheetDetail | None


class CharacterCreate(BaseModel):
    name: str
    concept: TextInput = None
    summary: TextInput = None
    sheet: bool | None = None


class ApprovalItem(_Response):
    id: str
    sheet_id: str | None
    character_id: str | None
    character_name: str
    owner: SnowflakeInput
    owner_name: str | None
    note: str
    requested_at: int


class ApprovalList(_Response):
    approvals: list[ApprovalItem]


class ApprovalDecision(BaseModel):
    decision: Literal["approve", "reject"]
    note: str = ""


class SearchResults(_Response):
    results: list[Track]


class ErrorDetail(_Response):
    code: str
    message: str


class ErrorEnvelope(_Response):
    error: ErrorDetail


TableStatus = Literal["open", "closed"]
TableRole = Literal["narrator", "player", "pending", "spectator"]
TokenColor = Annotated[str, BeforeValidator(_token_color)]
TokenLabel = Annotated[str, BeforeValidator(_clean_label)]


class TableScene(_Response):
    id: str
    slug: str
    name: str
    source: SceneSource
    width: int
    height: int
    grid: SceneGrid
    fog_outside: bool
    zones: list[SceneZone]
    fog: list[SceneRect] = []
    map_url: str
    saved: bool = True


class TableToken(_Response):
    id: str
    character_id: str | None
    label: str
    owner_id: SnowflakeInput
    x: float
    y: float
    w: int
    h: int
    color: str
    visible: bool
    rev: int


class TableTurn(_Response):
    id: str
    round: int
    token_id: str | None
    character_id: str | None
    label: str
    owner_id: SnowflakeInput
    started_at: int


class TableParticipant(_Response):
    token_id: str
    character_id: str | None
    label: str
    owner_id: SnowflakeInput
    acted: bool


class TableSummary(_Response):
    id: str
    campaign: str
    channel_id: Snowflake
    name: str
    viewer_id: Snowflake
    role: TableRole
    status: TableStatus
    round: int
    spectators: bool
    scene: TableScene | None
    tokens: list[TableToken]
    turn: TableTurn | None = None
    participants: list[TableParticipant] = []
    warning: str | None = None


class TableOpen(BaseModel):
    campaign: str
    channel_id: Snowflake
    scene: str
    name: TextInput = None


class TableConflictDetail(_Response):
    error: ErrorDetail
    table: OpenTable


class TableSceneChange(BaseModel):
    scene: str


class TableTokenCreate(BaseModel):
    label: TokenLabel
    character_id: TextInput = None
    owner_id: SnowflakeInput = None
    x: float = Field(allow_inf_nan=False, ge=0)
    y: float = Field(allow_inf_nan=False, ge=0)
    w: int = Field(default=1, ge=1)
    h: int = Field(default=1, ge=1)
    color: TokenColor = "#e9dfc7"
    visible: bool = True


class TableTokenPatch(BaseModel):
    label: TokenLabel | None = None
    character_id: TextInput = None
    owner_id: SnowflakeInput = None
    x: float | None = Field(default=None, allow_inf_nan=False, ge=0)
    y: float | None = Field(default=None, allow_inf_nan=False, ge=0)
    w: int | None = Field(default=None, ge=1)
    h: int | None = Field(default=None, ge=1)
    color: TokenColor | None = None
    visible: bool | None = None


class TableSpectators(BaseModel):
    enabled: bool


TurnAction = Literal["open", "pass", "end"]


class TableTurnRequest(BaseModel):
    action: TurnAction
    token_id: TextInput = None
    expected_turn_id: TextInput = None


class ReloadEvent(_Response):
    scope: str


class SheetConflictField(_Response):
    id: str
    sheet_id: str
    character_id: str | None
    field_path: str
    base: str | None
    ours: str | None
    theirs: str | None
    allow_both: bool


class SheetConflictList(_Response):
    conflicts: list[SheetConflictField]


class SheetConflictDetail(_Response):
    error: ErrorDetail
    conflicts: list[SheetConflictField]


class SheetConflictDecision(BaseModel):
    decision: Literal["ours", "theirs", "both"]


class SheetActionResult(_Response):
    action: Literal["restore", "forget"]
    sheet_id: str


class SseEnvelope(
    RootModel[
        StatusSnapshot
        | ReloadEvent
        | Presence
        | Position
        | Heartbeat
        | Directory
    ]
):
    """Frames emitted by GET /api/events; the event name travels out of band."""

    __sse__ = True


class ConnectRequest(BaseModel):
    guild_id: SnowflakeInput = None
    channel_id: SnowflakeInput = None


class SearchRequest(BaseModel):
    term: TextInput = None


class UrlRequest(BaseModel):
    url: TextInput = None


class LoopRequest(BaseModel):
    mode: TextInput = None


class SeekRequest(BaseModel):
    position: NumberInput = None


class VolumeRequest(BaseModel):
    volume: NumberInput = None


class LayerIdRequest(BaseModel):
    layer_id: TextInput = None


class LayerVolumeRequest(BaseModel):
    layer_id: TextInput = None
    volume: NumberInput = None


SSE_EVENTS: dict[str, type[BaseModel]] = {
    "status": StatusSnapshot,
    "reload": ReloadEvent,
    "presence": Presence,
    "position": Position,
    "heartbeat": Heartbeat,
    "directory": Directory,
}
