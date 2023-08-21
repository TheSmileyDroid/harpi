import asyncio
from time import sleep
from typing import Optional
from discord import VoiceClient
import discord
from discord.ext import commands

from src.res.interfaces.imessageparser import IMessageParser
from src.res.interfaces.imusicdata import IMusicData
from src.res.interfaces.imusicqueue import IMusicQueue


from ..interfaces.iguildsdata import IGuildsData
from ..interfaces.imusicplayer import IMusicPlayer
from .ytmusicdata import YTMusicData


class MusicPlayer(IMusicPlayer):
    def __init__(
        self,
        guilddata: IGuildsData,
        ctx: commands.Context,
        voice_client: VoiceClient,
        output: Optional[IMessageParser] = None,
    ) -> None:
        self.guild_data: IGuildsData = guilddata
        self.ctx: commands.Context = ctx
        self.voice_client: VoiceClient = voice_client
        self.output: Optional[IMessageParser] = output

    async def start(self):
        queue: IMusicQueue = self.guild_data.queue(self.ctx)
        if queue.get_length() == 0:
            return
        if self.voice_client.is_playing():
            sleep(0.5)
            if self.voice_client.is_playing():
                return

        music: IMusicData = queue.get_current()
        source = await music.get_source()
        self.voice_client.play(
            source,
            after=lambda e: asyncio.run_coroutine_threadsafe(
                self.go_next(), self.ctx.bot.loop
            ),
        )
        if isinstance(source, discord.FFmpegPCMAudio):
            source.volume = self.guild_data.volume(self.ctx) / 100

    async def go_next(self, skip: bool = False):
        if self.guild_data.skip_flag(self.ctx) and not skip:
            return
        if skip or not self.guild_data.is_looping(self.ctx):
            queue: IMusicQueue = self.guild_data.queue(self.ctx)
            queue.remove_current()
            self.guild_data.set_skip_flag(self.ctx, False)

        await self.start()

    async def play(self, text: str):
        data: list[YTMusicData] = YTMusicData.from_url(text)
        queue = self.guild_data.queue(self.ctx)

        for music in data:
            queue.add(music)

        if self.voice_client.is_playing():
            if self.output:
                musics_str = "\n".join([f"**{music.get_title()}**" for music in data])
                await self.output.send(f"Adicionado à fila:\n{musics_str}")
            return

        await self.start()

        if self.output:
            await self.output.send(f"Tocando agora: **{data[0].get_title()}**")

            musics_str = "\n".join([f"{music.get_title()}" for music in data[1:]])
            if musics_str:
                await self.output.send(
                    f"Playlist adicionada à fila:\n{musics_str}",
                )

    async def stop(self):
        queue = self.guild_data.queue(self.ctx)
        queue.clear()
        if self.output:
            await self.output.send("Parando a música")

        self.voice_client.stop()

    async def skip(self):
        self.guild_data.set_skip_flag(self.ctx, True)
        self.voice_client.stop()
        await self.go_next(True)
        if self.output:
            await self.output.send("Pulando a música")

    async def pause(self):
        self.voice_client.pause()
        if self.output:
            await self.output.send("Pausando a música")

    async def resume(self):
        self.voice_client.resume()
        if self.output:
            await self.output.send("Retomando a música")

    async def set_loop(self, loop: bool):
        self.guild_data.set_looping(self.ctx, loop)
        if self.output:
            await self.output.send(f"Loop {'ativado' if loop else 'desativado'}")

    async def get_volume(self) -> float:
        return self.guild_data.volume(self.ctx)

    async def set_volume(self, volume: float):
        self.guild_data.set_volume(self.ctx, volume)
        source: Optional[discord.AudioSource] = self.voice_client.source
        if source and isinstance(source, discord.PCMVolumeTransformer):
            source.volume = volume / 100
            if self.output:
                await self.output.send(f"Volume alterado para {volume}%")

    async def queue(self) -> IMusicQueue:
        return self.guild_data.queue(self.ctx)

    async def remove(self, index: int) -> None:
        queue = self.guild_data.queue(self.ctx)
        queue.remove(queue.get(index))
        if self.output:
            await self.output.send("Removido da fila")

    async def get_current(self) -> IMusicData:
        return self.guild_data.queue(self.ctx).get_current()

    async def shuffle(self) -> None:
        if self.output:
            await self.output.send("Embaralhando a fila")
        return self.guild_data.queue(self.ctx).shuffle()
