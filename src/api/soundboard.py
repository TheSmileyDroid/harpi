"""REST API endpoints for soundboard presets and live audio control."""

from __future__ import annotations

from typing import Any

from loguru import logger
from pydantic import BaseModel
from quart import Blueprint, request
from quart_schema import validate_request, validate_response

from src.HarpiLib.api import _has_path_to_output
from src.HarpiLib.soundboard.preset_store import PresetStore, SoundboardPreset
from src.HarpiLib.soundboard.source_manager import SoundboardSourceManager

bp = Blueprint("soundboard", __name__)
preset_store = PresetStore()
source_managers: dict[int, SoundboardSourceManager] = {}


# === Response Models ===


class PresetResponse(BaseModel):
    id: str
    name: str
    guild_id: int
    nodes: list[dict[str, Any]]
    edges: list[dict[str, Any]]
    created_at: str
    updated_at: str


def to_preset_response(preset: SoundboardPreset) -> PresetResponse:
    return PresetResponse(
        id=preset.id,
        name=preset.name,
        guild_id=preset.guild_id,
        nodes=preset.nodes,
        edges=preset.edges,
        created_at=preset.created_at,
        updated_at=preset.updated_at,
    )


class PresetListResponse(BaseModel):
    id: str
    name: str
    created_at: str
    updated_at: str


class ConnectionResponse(BaseModel):
    status: str
    channel_id: int | None = None
    error: str | None = None


class ActiveNodeStatus(BaseModel):
    node_id: str
    layer_id: str
    playing: bool
    volume: float
    progress: float
    duration: float
    title: str
    url: str


class SoundboardGraphResponse(BaseModel):
    nodes: list[dict[str, Any]]
    edges: list[dict[str, Any]]


class SoundboardStatusResponse(BaseModel):
    connected: bool
    channel_id: int | None
    channel_name: str | None
    active_nodes: list[ActiveNodeStatus]
    graph: SoundboardGraphResponse | None


class SourceActionResponse(BaseModel):
    status: str
    layer_id: str | None = None
    node_id: str | None = None
    error: str | None = None


class SourceVolumeResponse(BaseModel):
    status: str
    node_id: str
    volume: float
    error: str | None = None


class MetadataResponse(BaseModel):
    title: str
    duration: float
    url: str
    thumbnail: str | None = None
    error: str | None = None


# === Request Models ===


class MetadataRequest(BaseModel):
    url: str


class UpdateGraphRequest(BaseModel):
    nodes: list[dict[str, Any]]
    edges: list[dict[str, Any]]


class CreatePresetRequest(BaseModel):
    guild_id: int
    name: str
    nodes: list[dict[str, Any]] = []
    edges: list[dict[str, Any]] = []


class UpdatePresetRequest(BaseModel):
    guild_id: int
    name: str | None = None
    nodes: list[dict[str, Any]] | None = None
    edges: list[dict[str, Any]] | None = None


class ConnectSoundboardRequest(BaseModel):
    channel_id: int


class StartSourceRequest(BaseModel):
    guild_id: str
    channel_id: str | None = None
    node_id: str
    url: str
    volume: float = 100.0


class StopSourceRequest(BaseModel):
    guild_id: str
    node_id: str


class SourceVolumeRequest(BaseModel):
    guild_id: str
    node_id: str
    volume: float


class StartNodeRequest(BaseModel):
    guild_id: str
    node_id: str
    url: str
    volume: float = 100.0
    loop: bool = False


class StopNodeRequest(BaseModel):
    guild_id: str
    node_id: str


class NodeVolumeRequest(BaseModel):
    guild_id: str
    node_id: str
    volume: float


class NodeLoopRequest(BaseModel):
    guild_id: str
    node_id: str
    loop: bool


def get_source_manager(guild_id: int) -> SoundboardSourceManager:
    """Get or create a source manager for a guild."""
    if guild_id not in source_managers:
        from src.discord_bot import get_bot_instance

        bot = get_bot_instance()
        if bot:
            source_managers[guild_id] = SoundboardSourceManager(
                bot.api, guild_id
            )
    return source_managers.get(guild_id)


# === Preset CRUD ===


@bp.route("/api/soundboard/presets", methods=["GET"])
@validate_response(list[PresetListResponse])
async def list_presets():
    """List all presets for a guild."""
    guild_id_str = request.args.get("guild_id")
    if not guild_id_str:
        return [], 400

    try:
        guild_id = int(guild_id_str)
    except ValueError:
        return [], 400

    presets = preset_store.list_presets(guild_id)
    return [
        PresetListResponse(
            id=p.id,
            name=p.name,
            created_at=p.created_at,
            updated_at=p.updated_at,
        )
        for p in presets
    ]


@bp.route("/api/soundboard/presets/<preset_id>", methods=["GET"])
@validate_response(PresetResponse)
async def get_preset(preset_id: str):
    """Get a specific preset."""
    guild_id_str = request.args.get("guild_id")
    if not guild_id_str:
        return PresetResponse(
            id="",
            name="",
            guild_id=0,
            nodes=[],
            edges=[],
            created_at="",
            updated_at="",
        ), 400

    try:
        guild_id = int(guild_id_str)
    except ValueError:
        return PresetResponse(
            id="",
            name="",
            guild_id=0,
            nodes=[],
            edges=[],
            created_at="",
            updated_at="",
        ), 400

    preset = preset_store.get_preset(preset_id, guild_id)
    if not preset:
        return PresetResponse(
            id="",
            name="",
            guild_id=0,
            nodes=[],
            edges=[],
            created_at="",
            updated_at="",
        ), 404

    return to_preset_response(preset)


@bp.route("/api/soundboard/presets", methods=["POST"])
@validate_request(CreatePresetRequest)
@validate_response(PresetResponse)
async def create_preset(data: CreatePresetRequest):
    """Create a new preset."""
    guild_id = data.guild_id
    name = data.name
    nodes = data.nodes
    edges = data.edges

    if not name:
        return PresetResponse(
            id="",
            name="",
            guild_id=0,
            nodes=[],
            edges=[],
            created_at="",
            updated_at="",
        ), 400

    preset = preset_store.create_preset(guild_id, name, nodes, edges)
    return to_preset_response(preset), 201


@bp.route("/api/soundboard/presets/<preset_id>", methods=["PUT"])
@validate_request(UpdatePresetRequest)
@validate_response(PresetResponse)
async def update_preset(preset_id: str, data: UpdatePresetRequest):
    """Update an existing preset."""
    guild_id = data.guild_id

    preset = preset_store.update_preset(
        preset_id,
        guild_id,
        name=data.name,
        nodes=data.nodes,
        edges=data.edges,
    )

    if not preset:
        return PresetResponse(
            id="",
            name="",
            guild_id=0,
            nodes=[],
            edges=[],
            created_at="",
            updated_at="",
        ), 404

    return to_preset_response(preset)


class StatusResponse(BaseModel):
    status: str
    error: str | None = None


@bp.route("/api/soundboard/presets/<preset_id>", methods=["DELETE"])
@validate_response(StatusResponse)
async def delete_preset(preset_id: str):
    """Delete a preset."""
    guild_id_str = request.args.get("guild_id")
    if not guild_id_str:
        return StatusResponse(status="", error="guild_id required"), 400

    try:
        guild_id = int(guild_id_str)
    except ValueError:
        return StatusResponse(status="", error="Invalid guild_id"), 400

    success = preset_store.delete_preset(preset_id, guild_id)
    if not success:
        return StatusResponse(status="", error="Preset not found"), 404

    return StatusResponse(status="ok")


# === Soundboard Graph Management ===}


@bp.route("/api/soundboard/graph/<int:guild_id>", methods=["GET"])
@validate_response(SoundboardGraphResponse)
async def get_soundboard_graph(guild_id: int):
    """Get the current soundboard graph for a guild."""
    from src.discord_bot import get_bot_instance

    bot = get_bot_instance()
    if not bot:
        return SoundboardGraphResponse(nodes=[], edges=[]), 503

    graph = bot.api.get_soundboard_graph(guild_id)
    if not graph:
        return SoundboardGraphResponse(nodes=[], edges=[]), 404

    return SoundboardGraphResponse(nodes=graph.nodes, edges=graph.edges)


@bp.route("/api/soundboard/graph/<int:guild_id>", methods=["PUT"])
@validate_request(UpdateGraphRequest)
@validate_response(SoundboardGraphResponse)
async def update_soundboard_graph(guild_id: int, data: UpdateGraphRequest):
    """Update the soundboard graph for a guild."""
    from src.discord_bot import get_bot_instance

    bot = get_bot_instance()
    if not bot:
        return SoundboardGraphResponse(nodes=[], edges=[]), 503

    graph = await bot.api.update_soundboard_graph(
        guild_id, data.nodes, data.edges
    )
    return SoundboardGraphResponse(nodes=graph.nodes, edges=graph.edges)


# === Connection Management ===


@bp.route("/api/soundboard/connect/<int:guild_id>", methods=["POST"])
@validate_request(ConnectSoundboardRequest)
@validate_response(ConnectionResponse)
async def connect_soundboard(guild_id: int, data: ConnectSoundboardRequest):
    """Connect to voice channel for soundboard playback.

    Body:
        channel_id: The voice channel ID to connect to.
    """
    channel_id = data.channel_id

    from src.discord_bot import get_bot_instance

    bot = get_bot_instance()
    if not bot:
        return ConnectionResponse(status="", error="Bot not ready"), 503

    try:
        await bot.api.connect_to_voice(guild_id, channel_id)
        logger.info(
            f"Soundboard connected to channel {channel_id} in guild {guild_id}"
        )
        return ConnectionResponse(status="connected", channel_id=channel_id)
    except Exception as e:
        logger.error(f"Failed to connect soundboard: {e}")
        return ConnectionResponse(status="", error=str(e)), 500


@bp.route("/api/soundboard/disconnect/<int:guild_id>", methods=["POST"])
async def disconnect_soundboard(guild_id: int):
    """Disconnect soundboard from voice channel."""
    from src.discord_bot import get_bot_instance

    bot = get_bot_instance()
    if not bot:
        return ConnectionResponse(status="", error="Bot not ready"), 503

    manager = get_source_manager(guild_id)
    if manager:
        manager.stop_all()

    try:
        guild_config = bot.api.get_guild_config(guild_id)
        if guild_config and guild_config.voice_client:
            await guild_config.voice_client.disconnect()
        logger.info(f"Soundboard disconnected from guild {guild_id}")
        return ConnectionResponse(status="disconnected")
    except Exception as e:
        logger.error(f"Failed to disconnect soundboard: {e}")
        return ConnectionResponse(status="", error=str(e)), 500


@bp.route("/api/soundboard/status/<int:guild_id>", methods=["GET"])
@validate_response(SoundboardStatusResponse)
async def get_soundboard_status(guild_id: int):
    """Get soundboard connection and playback status."""
    from src.discord_bot import get_bot_instance

    bot = get_bot_instance()
    if not bot:
        return SoundboardStatusResponse(
            connected=False,
            channel_id=None,
            channel_name=None,
            active_nodes=[],
            graph=None,
        ), 503

    guild_config = bot.api.get_guild_config(guild_id)
    is_connected = (
        guild_config is not None
        and guild_config.voice_client is not None
        and guild_config.voice_client.is_connected()
    )

    # Build reverse mapping: layer_id -> node_id
    manager = get_source_manager(guild_id)
    layer_to_node: dict[str, str] = {}
    if manager:
        for nid, lid in manager._node_to_layer.items():
            layer_to_node[lid] = nid

    active_nodes = bot.api.get_background_audio_status(guild_id)
    node_statuses = []

    playing_node_ids: set[str] = set()
    for node in active_nodes:
        layer_id = node.get("layer_id", "")
        frontend_node_id = layer_to_node.get(layer_id, layer_id)

        if guild_config and guild_config.prepared_sources:
            for nid, source in guild_config.prepared_sources.items():
                if hasattr(source, "id") and source.id == layer_id:
                    frontend_node_id = nid
                    break

        playing_node_ids.add(frontend_node_id)
        node_statuses.append(
            ActiveNodeStatus(
                node_id=frontend_node_id,
                layer_id=layer_id,
                playing=True,
                volume=node.get("volume", 0),
                progress=node.get("progress", 0.0),
                duration=node.get("duration", 0.0),
                title=node.get("title", "Unknown"),
                url=node.get("url", ""),
            )
        )

    if guild_config and guild_config.prepared_sources:
        for node_id, source in guild_config.prepared_sources.items():
            if node_id not in playing_node_ids:
                duration = (
                    source.data.get("duration", 0)
                    if hasattr(source, "data")
                    else 0
                )
                node_statuses.append(
                    ActiveNodeStatus(
                        node_id=node_id,
                        layer_id="",
                        playing=False,
                        volume=source.volume * 100,
                        progress=getattr(source, "progress", 0.0),
                        duration=float(duration) if duration else 0.0,
                        title=getattr(source, "title", "Unknown"),
                        url=getattr(source, "url", ""),
                    )
                )

    graph = bot.api.get_soundboard_graph(guild_id)
    graph_response = None
    if graph:
        graph_response = SoundboardGraphResponse(
            nodes=graph.nodes, edges=graph.edges
        )

    return SoundboardStatusResponse(
        connected=is_connected,
        channel_id=guild_config.channel.id
        if guild_config and guild_config.channel
        else None,
        channel_name=guild_config.channel.name
        if guild_config and guild_config.channel
        else None,
        active_nodes=node_statuses,
        graph=graph_response,
    )


# === Source Management ===


@bp.route("/api/soundboard/source/start", methods=["POST"])
@validate_request(StartSourceRequest)
@validate_response(SourceActionResponse)
async def start_source(data: StartSourceRequest):
    """Start playing a source (adds as background layer).

    Body:
        guild_id: The guild ID.
        channel_id: The voice channel ID (required if not connected).
        node_id: Unique node identifier for this source.
        url: The audio URL.
        volume: Initial volume (0-200, default 100).
    """
    from src.discord_bot import get_bot_instance

    try:
        guild_id = int(data.guild_id)
        channel_id = int(data.channel_id) if data.channel_id else None
    except (ValueError, TypeError):
        return SourceActionResponse(
            status="", error="Invalid guild_id or channel_id"
        ), 400

    bot = get_bot_instance()
    if not bot:
        return SourceActionResponse(status="", error="Bot not ready"), 503

    manager = get_source_manager(guild_id)
    if not manager:
        return SourceActionResponse(
            status="", error="Failed to create source manager"
        ), 500

    try:
        layer_id = await manager.start_source(
            data.node_id, data.url, data.volume, channel_id
        )
        logger.info(f"Started source {data.node_id} as layer {layer_id}")
        return SourceActionResponse(
            status="started", layer_id=str(layer_id), node_id=data.node_id
        )
    except Exception as e:
        logger.error(f"Failed to start source: {e}")
        return SourceActionResponse(status="", error=str(e)), 500


@bp.route("/api/soundboard/source/stop", methods=["POST"])
@validate_request(StopSourceRequest)
@validate_response(SourceActionResponse)
async def stop_source(data: StopSourceRequest):
    """Stop a source (removes background layer).

    Body:
        guild_id: The guild ID.
        node_id: The node identifier to stop.
    """
    try:
        guild_id = int(data.guild_id)
    except (ValueError, TypeError):
        return SourceActionResponse(status="", error="Invalid guild_id"), 400

    manager = get_source_manager(guild_id)
    if not manager:
        return SourceActionResponse(
            status="", error="No source manager for guild"
        ), 404

    try:
        manager.stop_source(data.node_id)
        logger.info(f"Stopped source {data.node_id}")
        return SourceActionResponse(status="stopped", node_id=data.node_id)
    except Exception as e:
        logger.error(f"Failed to stop source: {e}")
        return SourceActionResponse(status="", error=str(e)), 500


@bp.route("/api/soundboard/source/volume", methods=["POST"])
@validate_request(SourceVolumeRequest)
@validate_response(SourceVolumeResponse)
async def set_source_volume(data: SourceVolumeRequest):
    """Set volume for a source.

    Body:
        guild_id: The guild ID.
        node_id: The node identifier.
        volume: Volume level (0-200).
    """
    try:
        guild_id = int(data.guild_id)
    except (ValueError, TypeError):
        return SourceVolumeResponse(
            status="",
            node_id="",
            volume=0.0,
            error="Invalid guild_id",
        ), 400

    manager = get_source_manager(guild_id)
    if not manager:
        return SourceVolumeResponse(
            status="",
            node_id="",
            volume=0.0,
            error="No source manager for guild",
        ), 404

    try:
        manager.set_volume(data.node_id, data.volume)
        return SourceVolumeResponse(
            status="ok", node_id=data.node_id, volume=data.volume
        )
    except Exception as e:
        logger.error(f"Failed to set volume: {e}")
        return SourceVolumeResponse(
            status="", node_id=data.node_id, volume=data.volume, error=str(e)
        ), 500


@bp.route("/api/soundboard/stop/<int:guild_id>", methods=["POST"])
@validate_response(StatusResponse)
async def stop_all_sources(guild_id: int):
    """Stop all soundboard sources for a guild."""
    manager = get_source_manager(guild_id)
    if manager:
        manager.stop_all()

    return StatusResponse(status="ok")


# === Node Operations (Sound Source Management) ===}


@bp.route("/api/soundboard/node/metadata", methods=["POST"])
@validate_request(MetadataRequest)
@validate_response(MetadataResponse)
async def fetch_node_metadata(data: MetadataRequest):
    """Fetch metadata for a URL without starting playback.

    Body:
        url: The audio URL (YouTube, etc).
    """
    from src.HarpiLib.musicdata.ytmusicdata import YTMusicData

    try:
        music_data_list = await YTMusicData.from_url(data.url)
        if not music_data_list:
            return MetadataResponse(
                title="",
                duration=0.0,
                url=data.url,
                error="No results found",
            ), 404

        md = music_data_list[0]
        return MetadataResponse(
            title=md.title,
            duration=float(md.duration),
            url=md.get_url(),
            thumbnail=md.thumbnail,
        )
    except Exception as e:
        logger.error(f"Failed to fetch metadata: {e}")
        return MetadataResponse(
            title="",
            duration=0.0,
            url=data.url,
            error=str(e),
        ), 500


@bp.route("/api/soundboard/node/start", methods=["POST"])
@validate_request(StartNodeRequest)
@validate_response(SourceActionResponse)
async def start_node(data: StartNodeRequest):
    """Prepare a sound source node (load but don't play yet).

    Body:
        guild_id: The guild ID.
        node_id: Unique node identifier for this source.
        url: The audio URL.
        volume: Initial volume (0-200, default 100).
        loop: Whether to loop the audio (default false).
    """
    from src.discord_bot import get_bot_instance

    try:
        guild_id = int(data.guild_id)
    except (ValueError, TypeError):
        return SourceActionResponse(status="", error="Invalid guild_id"), 400

    bot = get_bot_instance()
    if not bot:
        return SourceActionResponse(
            status="", node_id=data.node_id, error="Bot not ready"
        ), 503

    guild_config = bot.api.get_guild_config(guild_id)
    if not guild_config:
        return SourceActionResponse(
            status="", node_id=data.node_id, error="Not connected to voice"
        ), 400

    try:
        if data.node_id not in guild_config.prepared_sources:
            await bot.api.prepare_source(
                guild_id, data.node_id, data.url, data.volume
            )
            logger.info(f"Prepared node {data.node_id}")

        graph = bot.api.get_soundboard_graph(guild_id)
        if graph and _has_path_to_output(
            data.node_id, graph.nodes, graph.edges
        ):
            await bot.api.start_source_playback(guild_id, data.node_id)
            logger.info(f"Started playback for node {data.node_id}")

        return SourceActionResponse(status="prepared", node_id=data.node_id)
    except Exception as e:
        logger.error(f"Failed to prepare node: {e}")
        return SourceActionResponse(
            status="", node_id=data.node_id, error=str(e)
        ), 500


@bp.route("/api/soundboard/node/loop", methods=["POST"])
@validate_request(NodeLoopRequest)
@validate_response(SourceActionResponse)
async def set_node_loop(data: NodeLoopRequest):
    """Set loop for a node.

    Body:
        guild_id: The guild ID.
        node_id: The node identifier.
        loop: Whether to loop the audio.
    """
    from src.discord_bot import get_bot_instance

    try:
        guild_id = int(data.guild_id)
    except (ValueError, TypeError):
        return SourceActionResponse(status="", error="Invalid guild_id"), 400

    bot = get_bot_instance()
    if not bot:
        return SourceActionResponse(status="", error="Bot not ready"), 503

    try:
        graph = bot.api.get_soundboard_graph(guild_id)
        if graph:
            for node in graph.nodes:
                if node.get("id") == data.node_id:
                    node["data"]["loop"] = data.loop
                    break

        logger.info(f"Set loop={data.loop} for node {data.node_id}")
        return SourceActionResponse(status="ok", node_id=data.node_id)
    except Exception as e:
        logger.error(f"Failed to set loop: {e}")
        return SourceActionResponse(status="", error=str(e)), 500


@bp.route("/api/soundboard/node/stop", methods=["POST"])
@validate_request(StopNodeRequest)
@validate_response(SourceActionResponse)
async def stop_node(data: StopNodeRequest):
    """Stop a sound source node - stops playback and unloads.

    Body:
        guild_id: The guild ID.
        node_id: The node identifier to stop.
    """
    from src.discord_bot import get_bot_instance

    try:
        guild_id = int(data.guild_id)
    except (ValueError, TypeError):
        return SourceActionResponse(status="", error="Invalid guild_id"), 400

    bot = get_bot_instance()
    if not bot:
        return SourceActionResponse(
            status="", node_id=data.node_id, error="Bot not ready"
        ), 503

    guild_config = bot.api.get_guild_config(guild_id)
    if not guild_config:
        return SourceActionResponse(
            status="", node_id=data.node_id, error="Not connected to voice"
        ), 400

    try:
        await bot.api.stop_source_playback(guild_id, data.node_id)

        if data.node_id in guild_config.prepared_sources:
            source = guild_config.prepared_sources.pop(data.node_id)
            if hasattr(source, "cleanup"):
                source.cleanup()
            logger.info(f"Unloaded prepared source {data.node_id}")

        logger.info(f"Stopped node {data.node_id}")
        return SourceActionResponse(status="stopped", node_id=data.node_id)
    except Exception as e:
        logger.error(f"Failed to stop node: {e}")
        return SourceActionResponse(
            status="", node_id=data.node_id, error=str(e)
        ), 500


@bp.route("/api/soundboard/node/volume", methods=["POST"])
@validate_request(NodeVolumeRequest)
@validate_response(SourceVolumeResponse)
async def set_node_volume(data: NodeVolumeRequest):
    """Set volume for a node.

    Body:
        guild_id: The guild ID.
        node_id: The node identifier.
        volume: Volume level (0-200).
    """
    try:
        guild_id = int(data.guild_id)
        volume = float(data.volume)
    except (ValueError, TypeError):
        return SourceVolumeResponse(
            status="",
            node_id=data.node_id,
            volume=0.0,
            error="Invalid guild_id or volume",
        ), 400

    manager = get_source_manager(guild_id)
    if not manager:
        return SourceVolumeResponse(
            status="",
            node_id=data.node_id,
            volume=0.0,
            error="No source manager for guild",
        ), 404

    try:
        manager.set_volume(data.node_id, volume)
        return SourceVolumeResponse(
            status="ok", node_id=data.node_id, volume=volume
        )
    except Exception as e:
        logger.error(f"Failed to set volume: {e}")
        return SourceVolumeResponse(
            status="", node_id=data.node_id, volume=data.volume, error=str(e)
        ), 500
