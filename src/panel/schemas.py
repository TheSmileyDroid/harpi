from __future__ import annotations

import math
from typing import Annotated, Any, Literal

from pydantic import BaseModel, BeforeValidator, ConfigDict, RootModel


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


Snowflake = Annotated[str, BeforeValidator(_as_snowflake)]
SnowflakeInput = Annotated[str | None, BeforeValidator(_optional_snowflake)]
TextInput = Annotated[str | None, BeforeValidator(_clean_text)]
NumberInput = Annotated[float | None, BeforeValidator(_finite_number)]


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


SheetStatus = Literal["active", "pending", "archived"]
SheetReadState = Literal["ok", "invalid"]


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


class CharacterDetail(_Response):
    kind: Literal["sheet", "card"]
    card: CharacterCard
    sheet: SheetDetail | None


class SearchResults(_Response):
    results: list[Track]


class ErrorDetail(_Response):
    code: str
    message: str


class ErrorEnvelope(_Response):
    error: ErrorDetail


class ReloadEvent(_Response):
    scope: str


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
