"""Background audio management service.

Thread safety
-------------
Background audio layers are stored in ``GuildConfig.background`` (a dict).
Writes happen on the bot's event loop (add/remove layer).  The
``on_track_end`` callback from ``MixerSource`` (voice-sending thread)
schedules dict mutation via ``bot.loop.call_soon_threadsafe`` rather than
mutating directly (see ``MusicQueueService``).

Volume adjustments (``set_background_volume``) write to
``YoutubeDLSource.volume``, a simple float attribute — atomic under
CPython's GIL.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from discord.ext.commands import Bot, Context

from src.harpi_lib.music.ytmusicdata import YoutubeDLSource, YTMusicData

if TYPE_CHECKING:
    from src.harpi_lib.api import GuildConfig
    from src.harpi_lib.services.voice_connection import VoiceConnectionService


class BackgroundAudioService:
    """Manages background audio layers (ambient sounds, etc.)."""

    def __init__(
        self,
        bot: Bot,
        guilds: dict[int, GuildConfig],
        voice_service: VoiceConnectionService,
    ) -> None:
        self.bot = bot
        self.guilds = guilds
        self.voice_service = voice_service

    async def add(
        self,
        guild_id: int,
        channel_id: int,
        link: str,
        ctx: Context | None = None,
    ) -> str:
        """Add a background audio layer from a URL."""
        music_data_list = await YTMusicData.from_url(link)
        if not music_data_list:
            raise ValueError(f"No audio found for URL: {link}")
        guild_config = self.guilds.get(guild_id)
        if not guild_config:
            guild_config = await self.voice_service.connect(
                guild_id, channel_id, ctx
            )
        source = await YoutubeDLSource.from_music_data(music_data_list[0])
        source.volume = 0.7
        layer_id = guild_config.controller.add_layer(source)
        if not guild_config.background:
            guild_config.background = {}
        guild_config.background[layer_id] = source
        return layer_id

    async def remove(self, guild_id: int, layer_id: str) -> YoutubeDLSource:
        """Remove a background audio layer by ID."""
        guild_config = self.guilds.get(guild_id)
        if not guild_config:
            raise ValueError("Guilda não conectada")
        if (
            not guild_config.background
            or layer_id not in guild_config.background
        ):
            raise ValueError("Layer não encontrado")

        found_layer = guild_config.background.pop(layer_id)
        guild_config.controller.remove_layer(layer_id)
        return found_layer

    async def set_volume(
        self, guild_id: int, layer_id: str, volume: float
    ) -> None:
        """Set the volume for a specific background audio layer."""
        guild_config = self.guilds.get(guild_id)
        if not guild_config:
            raise ValueError("Guilda não conectada")
        if (
            not guild_config.background
            or layer_id not in guild_config.background.keys()
        ):
            raise ValueError(
                f"Layer {layer_id} não encontrado em {guild_config.background.keys() if guild_config.background else 'Nenhuma guilda'}"
            )

        guild_config.background[layer_id].volume = max(0.0, min(2.0, volume))

    def get_status(self, guild_id: int) -> list[dict[str, Any]]:
        """Get status info for all background audio layers."""
        guild_config = self.guilds.get(guild_id)
        if not guild_config or not guild_config.background:
            return []

        status = []
        for layer_id, source in guild_config.background.items():
            duration = (
                source.data.get("duration", 0)
                if hasattr(source, "data")
                else 0
            )
            status.append({
                "layer_id": layer_id,
                "playing": True,
                "volume": source.volume * 100,
                "progress": getattr(source, "progress", 0.0),
                "duration": float(duration) if duration else 0.0,
                "title": getattr(source, "title", "Unknown"),
                "url": getattr(source, "url", ""),
            })
        return status

    async def clean_all(self, guild_id: int) -> None:
        """Remove all background audio layers."""
        guild_config = self.guilds.get(guild_id)
        if not guild_config:
            raise ValueError("Guilda não conectada")
        guild_config.controller.cleanup_all()
        if guild_config.background:
            guild_config.background.clear()
