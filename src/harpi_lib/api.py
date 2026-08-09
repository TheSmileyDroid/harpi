"""HarpiAPI facade delegating to specialized service classes."""

from dataclasses import dataclass

import discord
from discord.channel import VoiceChannel
from discord.ext.commands import Context

from src.harpi_lib.audio.controller import AudioController
from src.harpi_lib.audio.mixer import MixerSource
from src.harpi_lib.audio.session import LoopMode
from src.harpi_lib.music.ytmusicdata import YTMusicData


@dataclass
class GuildConfig:
    id: int
    mixer: MixerSource
    controller: AudioController
    ctx: Context | None = None
    voice_client: discord.VoiceClient | None = None
    queue: list[YTMusicData] | None = None
    current_music: YTMusicData | None = None
    loop: LoopMode = LoopMode.OFF
    channel: VoiceChannel | None = None
    volume: float = 0.7
