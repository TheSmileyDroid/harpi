"""Socket.IO integration for real-time soundboard sync.

Thread safety
-------------
``_active_guilds`` (module-level ``set[int]``) is mutated only from
Socket.IO event handlers, which run on a single async event loop.
No lock is required.  This is a **LOW severity** accepted risk.
"""

from __future__ import annotations

from typing import Any

import socketio
from loguru import logger

from src.harpi_lib.soundboard.preset_store import PresetStore

sio = socketio.AsyncServer(async_mode="asgi", cors_allowed_origins="*")
preset_store = PresetStore()

_active_guilds: set[int] = set()


@sio.event
async def connect(sid: str, environ: dict) -> None:
    logger.debug(f"Client connected: {sid}")


@sio.event
async def disconnect(sid: str) -> None:
    logger.debug(f"Client disconnected: {sid}")


@sio.event
async def join_guild(sid: str, guild_id: int) -> None:
    """Subscribe to updates for a specific guild."""
    await sio.enter_room(sid, f"guild_{guild_id}")
    _active_guilds.add(guild_id)
    logger.debug(f"Client {sid} joined guild {guild_id}")


@sio.event
async def leave_guild(sid: str, guild_id: int) -> None:
    """Unsubscribe from guild updates."""
    await sio.leave_room(sid, f"guild_{guild_id}")
    logger.debug(f"Client {sid} left guild {guild_id}")


async def broadcast_preset_update(
    guild_id: int, preset_id: str, action: str
) -> None:
    """Broadcast a preset update to all clients in a guild room."""
    await sio.emit(
        "preset_updated",
        {"preset_id": preset_id, "action": action},
        room=f"guild_{guild_id}",
    )


async def broadcast_execution_status(
    guild_id: int, status: str, message: str = ""
) -> None:
    """Broadcast soundboard execution status."""
    await sio.emit(
        "execution_status",
        {"status": status, "message": message},
        room=f"guild_{guild_id}",
    )


async def broadcast_node_state(
    guild_id: int, node_id: str, state: dict[str, Any]
) -> None:
    """Broadcast a node state change (playing/stopped/etc)."""
    await sio.emit(
        "node_state_change",
        {"node_id": node_id, "state": state},
        room=f"guild_{guild_id}",
    )


def create_socketio_app() -> socketio.ASGIApp:
    """Create the ASGI app for Socket.IO."""
    return socketio.ASGIApp(sio)
