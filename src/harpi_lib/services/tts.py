"""Text-to-speech playback service."""

from __future__ import annotations

from typing import TYPE_CHECKING

import discord
from discord.ext.commands import Bot, Context
from loguru import logger

if TYPE_CHECKING:
    from src.harpi_lib.api import GuildConfig
    from src.harpi_lib.services.voice_connection import VoiceConnectionService


class TTSService:
    """Manages text-to-speech audio playback."""

    def __init__(
        self,
        bot: Bot,
        guilds: dict[int, GuildConfig],
        voice_service: VoiceConnectionService,
    ) -> None:
        self.bot = bot
        self.guilds = guilds
        self.voice_service = voice_service

    async def play(
        self,
        guild_id: int,
        channel_id: int,
        source: discord.AudioSource,
        ctx: Context | None = None,
    ) -> None:
        """Play a TTS audio source in a voice channel."""
        guild_config = self.guilds.get(guild_id)
        if not guild_config:
            logger.info(
                "TTS: no existing guild config for guild {}, connecting to channel {}",
                guild_id,
                channel_id,
            )
            guild_config = await self.voice_service.connect(
                guild_id, channel_id, ctx
            )
        logger.info("TTS: setting TTS track for guild {}", guild_id)
        guild_config.controller.set_tts_track(source)
