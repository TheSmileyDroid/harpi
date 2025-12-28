from collections.abc import Callable
from dataclasses import dataclass
from functools import partial
from typing import cast

import discord
from discord.ext.commands import Bot, Context

from src.HarpiLib.music.mixer import MixerSource
from src.HarpiLib.musicdata.ytmusicdata import (
    YoutubeDLSource,
    YTMusicData,
)


@dataclass
class GuildConfig:
    id: int
    mixer: MixerSource
    ctx: Context | None = None
    voice_client: discord.VoiceClient | None = None
    queue: list[YTMusicData] | None = None
    background: list[YoutubeDLSource] | None = None
    current_music: YTMusicData | None = None
    loop: bool = False


class HarpiAPI:
    def __init__(self, bot: Bot) -> None:
        self.bot: Bot = bot
        self.guilds: dict[int, GuildConfig] = {}

    def _guild(self, guild_id: int) -> discord.Guild:
        guild = self.bot.get_guild(guild_id)
        if not guild:
            raise ValueError("Servidor não encontrado")
        return guild

    def _voice_channel(
        self, guild: discord.Guild, channel_id: int
    ) -> discord.VoiceChannel:
        channel = guild.get_channel(channel_id)
        if not channel or not isinstance(channel, discord.VoiceChannel):
            raise ValueError("Canal de voz não encontrado")
        return channel

    async def connect_to_voice(
        self, guild_id: int, channel_id: int, ctx: Context | None = None
    ) -> GuildConfig:
        """Conecta ao canal de voz.

        Parameters
        ----------
        guild_id : int
            Identificador da guilda.
        channel_id : int
            Identificador do canal de voz.

        Raises
        ------
        ValueError
            Canal de voz não encontrado.
        ValueError
            Servidor não encontrado.
        """
        guild = self._guild(guild_id)

        channel = self._voice_channel(guild, channel_id)

        voice: discord.VoiceClient | None = cast(
            "discord.VoiceClient | None", guild.voice_client
        )
        if voice:
            await voice.disconnect()

        vc = await channel.connect()

        mixer = MixerSource()
        guild_config = self.guilds.get(
            guild.id,
            GuildConfig(id=guild.id, mixer=mixer, ctx=ctx, voice_client=vc),
        )
        callback = cast(
            Callable,
            partial(self._mixer_callback, guild_config=guild_config),
        )
        bg_callback = cast(
            Callable,
            partial(self._background_callback, guild_config=guild_config),
        )
        mixer.add_observer("queue_end", callback)
        mixer.add_observer("track_end", bg_callback)
        guild_config.ctx = ctx
        guild_config.mixer = mixer
        self.guilds[guild.id] = guild_config
        vc.play(mixer)

        return guild_config

    def _mixer_callback(self, guild_config: GuildConfig):
        if guild_config.queue and len(guild_config.queue) > 0:
            _ = self.bot.loop.create_task(self.next_music(guild_config))
        else:
            guild_config.current_music = None

    def _background_callback(
        self, guild_config: GuildConfig, to_remove: list[YoutubeDLSource]
    ):
        for bg in to_remove:
            if guild_config.background and bg in guild_config.background:
                guild_config.background.remove(bg)

    async def next_music(self, guild_config: GuildConfig):
        if not guild_config.queue or len(guild_config.queue) == 0:
            guild_config.current_music = None
            guild_config.mixer.set_current_from_queue(None)
            return
        if not guild_config.loop:
            music_data = guild_config.queue.pop(0)
            guild_config.current_music = music_data
            source = await YoutubeDLSource.from_music_data(music_data)
            guild_config.mixer.set_current_from_queue(source)
        else:
            music_data = guild_config.queue[0]
            guild_config.current_music = music_data
            source = await YoutubeDLSource.from_music_data(music_data)
            guild_config.mixer.set_current_from_queue(source)

    async def add_music_to_queue(
        self,
        guild_id: int,
        channel_id: int,
        link: str,
        ctx: Context | None = None,
    ):
        music_data_list = await YTMusicData.from_url(link)
        guild_config = self.guilds.get(
            guild_id,
        )
        if not guild_config:
            guild_config = await self.connect_to_voice(
                guild_id, channel_id, ctx
            )
        if not guild_config.queue:
            guild_config.queue = []
        guild_config.queue.extend(music_data_list)
        if not guild_config.current_music:
            await self.next_music(guild_config)

    async def stop_music(self, guild_id: int):
        guild_config = self.guilds.get(guild_id)
        if not guild_config:
            raise ValueError("Guilda não conectada")
        if not guild_config.queue:
            guild_config.queue = []
        guild_config.queue.clear()
        guild_config.mixer.set_current_from_queue(None)
        guild_config.current_music = None

    async def skip_music(self, guild_id: int):
        guild_config = self.guilds.get(guild_id)
        if not guild_config:
            raise ValueError("Guilda não conectada")
        await self.next_music(guild_config)

    async def disconnect_voice(self, guild_id: int):
        guild_config = self.guilds.get(guild_id)
        if not guild_config:
            raise ValueError("Guilda não conectada")
        voice_client = guild_config.voice_client
        if voice_client and voice_client.is_connected():
            await voice_client.disconnect()
        del self.guilds[guild_id]

    async def set_loop(self, guild_id: int, loop: bool):
        guild_config = self.guilds.get(guild_id)
        if not guild_config:
            raise ValueError("Guilda não conectada")
        guild_config.loop = loop

    def get_guild_config(self, guild_id: int) -> GuildConfig | None:
        return self.guilds.get(guild_id)

    async def add_background_audio(
        self,
        guild_id: int,
        channel_id: int,
        link: str,
        ctx: Context | None = None,
    ) -> None:
        music_data_list = await YTMusicData.from_url(link)
        guild_config = self.guilds.get(
            guild_id,
        )
        if not guild_config:
            guild_config = await self.connect_to_voice(
                guild_id, channel_id, ctx
            )
        source = await YoutubeDLSource.from_music_data(music_data_list[0])
        guild_config.mixer.add_track(source)
        if not guild_config.background:
            guild_config.background = []
        guild_config.background.append(source)

    async def play_tts_source(
        self,
        guild_id: int,
        channel_id: int,
        source: discord.AudioSource,
        ctx: Context | None = None,
    ) -> None:
        """Plays a TTS source."""
        guild_config = self.guilds.get(guild_id)
        if not guild_config:
            guild_config = await self.connect_to_voice(
                guild_id, channel_id, ctx
            )
        guild_config.mixer.set_tts_track(source)

    async def clean_background_audios(self, guild_id: int) -> None:
        guild_config = self.guilds.get(guild_id)
        if not guild_config:
            raise ValueError("Guilda não conectada")
        guild_config.mixer.cleanup()
