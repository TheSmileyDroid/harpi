"""Panel context: each page resolves only what it renders.

The base context covers the chrome every page shares (navigation, bot
status).  ``PAGE_RESOLVERS`` maps a page to the extra resolvers it needs:
the dashboard resolves server status and bot info, the music page resolves
the guild/channel selector (plus static fragment defaults), settings
resolves nothing.  Music playback data is never resolved by the page —
the HTMX fragments self-poll (queue 3s, playback 2s, layers 3s, status 5s).
"""

from __future__ import annotations

import platform
from dataclasses import asdict, dataclass, field
from typing import Any, Awaitable, Callable, cast

import discord
from discord import VoiceChannel
from quart import session

from src.api.deps import get_bot
from src.api.guild import _get_guilds
from src.api.music import MusicStatusResponse, get_music_data
from src.api.server_status import get_server_status

VERSION = "0.1.0"

NAV_ITEMS = [
    {"label": "DASHBOARD", "icon": "layout-dashboard", "page": "dashboard"},
    {"label": "MUSIC", "icon": "music", "page": "music"},
    {"label": "SETTINGS", "icon": "settings", "page": "settings"},
]


@dataclass
class MusicPanelContext:
    """Render context for the self-polling music fragments."""

    queue: list[Any] = field(default_factory=list)
    layers: list[Any] = field(default_factory=list)
    current_track: Any | None = None
    paused: bool = False
    volume: float = 0.5
    loop_mode: str = "off"
    current_position: int = 0
    current_position_formatted: str = "0:00"


def project_music_panel(
    status: MusicStatusResponse | None,
) -> MusicPanelContext:
    """Project the music read-model into the panel render context."""
    if status is None:
        return MusicPanelContext()
    total_seconds = status.progress // 1000
    minutes, seconds = divmod(total_seconds, 60)
    return MusicPanelContext(
        queue=status.queue,
        layers=status.layers,
        current_track=status.current_music,
        paused=status.is_paused,
        volume=status.volume,
        loop_mode=status.loop_mode,
        current_position=status.progress,
        current_position_formatted=f"{minutes}:{seconds:02d}",
    )


async def get_music_panel(guild_id: int) -> MusicPanelContext:
    """Fetch a guild's panel state through the bot-loop bridge."""
    return project_music_panel(await get_music_data(guild_id))


async def base_context() -> dict[str, Any]:
    """Context shared by every page: navigation and bot status."""
    bot = get_bot()
    return {
        "nav_items": NAV_ITEMS,
        "bot_connected": bot.is_ready() if bot else False,
    }


async def selector_context() -> dict[str, Any]:
    """Guild/channel selector context plus fragment render defaults."""
    bot = get_bot()
    guilds = await _get_guilds()
    raw_guild_id = session.get("guild_id")
    selected_guild_id = int(raw_guild_id) if raw_guild_id else None
    channels: list[Any] = []
    selected_channel: VoiceChannel | None = None
    if selected_guild_id and bot:
        guild = bot.get_guild(selected_guild_id)
        if guild:
            channels = guild.voice_channels
        for voice_client in bot.voice_clients:
            if (
                cast(VoiceChannel, voice_client.channel).guild.id
                == selected_guild_id
            ):
                selected_channel = cast(VoiceChannel, voice_client.channel)

    panel = MusicPanelContext()
    return {
        "guilds": guilds,
        "selected_guild_id": selected_guild_id,
        "selected_channel_id": selected_channel.id
        if selected_channel
        else None,
        "channels": channels,
        "guild_id": selected_guild_id,
        "channel_id": selected_channel.id if selected_channel else None,
        **asdict(panel),
    }


async def server_status_context() -> dict[str, Any]:
    """Server status cards for the dashboard."""
    bot = get_bot()
    guilds = await _get_guilds()
    status = await get_server_status(guilds, bot=bot)
    return {
        **status,
        "guild_count": len(guilds),
        "user_count": sum(g.member_count or 0 for g in guilds)
        if guilds
        else 0,
    }


async def bot_info_context() -> dict[str, Any]:
    """Bot and runtime information for the dashboard."""
    bot = get_bot()
    return {
        "bot_user": str(bot.user) if bot and bot.user else "Unknown",
        "bot_id": str(bot.user.id) if bot and bot.user else "Unknown",
        "discord_version": discord.__version__,
        "python_version": platform.python_version(),
        "version": VERSION,
    }


PAGE_RESOLVERS: dict[str, list[Callable[[], Awaitable[dict[str, Any]]]]] = {
    "dashboard": [server_status_context, bot_info_context],
    "music": [selector_context],
    "settings": [],
}


async def resolve_page_context(page: str) -> dict[str, Any]:
    """Build the render context for a page from its resolvers."""
    context = await base_context()
    for resolver in PAGE_RESOLVERS.get(page, []):
        context.update(await resolver())
    return context
