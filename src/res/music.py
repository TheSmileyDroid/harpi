from asyncio.queues import Queue
import enum
from random import choice
from typing import Optional
from discord import Member
from discord.app_commands import choices, describe
from discord.ext.commands import Bot, Cog, CommandError, Context, hybrid_command
from discord.ext.commands.bot import asyncio
from discord.voice_client import VoiceClient

from src.res.utils.ytmusicdata import YTMusicData, YoutubeDLSource


class LoopMode(enum.Enum):
    OFF = 0
    TRACK = 1
    QUEUE = 2


class MusicCog(Cog):
    def __init__(self, client: Bot) -> None:
        super().__init__()

        self.musicQueue: dict[int, list[YTMusicData]] = {}
        self.loopMap: dict[int, LoopMode] = {}
        self.playChannel: Queue[Context] = Queue()
        self.currentMusic: dict[int, Optional[YTMusicData]] = {}
        tasks = []
        for _i in range(3):
            task = asyncio.create_task(self.playLoop())
            tasks.append(task)

    async def join(self, ctx: Context) -> VoiceClient:
        if (
            not isinstance(ctx.author, Member)
            or not ctx.author.voice
            or not ctx.author.voice.channel
        ):
            raise CommandError("Você não está em um canal de voz")
        if ctx.voice_client is not None and isinstance(ctx.voice_client, VoiceClient):
            voiceChannel = ctx.author.voice.channel
            await ctx.voice_client.move_to(voiceChannel)
            return ctx.voice_client
        return await ctx.author.voice.channel.connect()

    @hybrid_command("play")
    @describe(link="Link da música a ser tocada")
    async def play(self, ctx: Context, *, link: str):
        if ctx.guild:
            musicDataList = await YTMusicData.from_url(link)
            queue = self.musicQueue.get(ctx.guild.id) or []
            for musicData in musicDataList:
                queue.append(musicData)
            self.musicQueue[ctx.guild.id] = queue
            await self.playChannel.put(ctx)
            await ctx.send(
                f'Adicionando à fila: {", ".join(map(lambda m: m.get_title(), musicDataList))}'
            )
        else:
            await ctx.send("Você não está numa guilda")
        pass

    @hybrid_command("stop")
    async def stop(self, ctx: Context):
        if not ctx.guild:
            raise CommandError("Você precisa estar em um canal para usar esse comando")
        voice = await self.join(ctx)
        self.musicQueue[ctx.guild.id] = []
        voice.stop()

    @hybrid_command("skip")
    async def skip(self, ctx: Context):
        voice = await self.join(ctx)
        voice.stop()

    @hybrid_command("pause")
    async def pause(self, ctx: Context):
        voice = await self.join(ctx)
        voice.pause()

    @hybrid_command("resume")
    async def resume(self, ctx: Context):
        voice = await self.join(ctx)
        voice.resume()

    @hybrid_command("loop")
    @describe(mode="Loop mode")
    async def loop(self, ctx: Context, mode: str):
        if not ctx.guild:
            raise CommandError("Você precisa estar em um canal para usar esse comando")
        if (
            mode == "off"
            or mode == "false"
            or mode == "0"
            or mode == "no"
            or mode == "n"
        ):
            self.loopMap[ctx.guild.id] = LoopMode.OFF
            print("Loop mode: OFF")
            await ctx.send("Loop mode: OFF")
        elif (
            mode == "track"
            or mode == "true"
            or mode == "1"
            or mode == "yes"
            or mode == "y"
            or mode == "musica"
        ):
            self.loopMap[ctx.guild.id] = LoopMode.TRACK
            print("Loop mode: TRACK")
            await ctx.send("Loop mode: TRACK")
        elif (
            mode == "queue"
            or mode == "q"
            or mode == "fila"
            or mode == "f"
            or mode == "lista"
            or mode == "l"
        ):
            self.loopMap[ctx.guild.id] = LoopMode.QUEUE
            print("Loop mode: QUEUE")
            await ctx.send("Loop mode: QUEUE")
        else:
            if self.loopMap.get(ctx.guild.id, LoopMode.OFF) is not LoopMode.OFF:
                self.loopMap[ctx.guild.id] = LoopMode.OFF
                print("Loop mode: OFF")
                await ctx.send("Loop mode: OFF")
            else:
                self.loopMap[ctx.guild.id] = LoopMode.TRACK
                print("Loop mode: TRACK")
                await ctx.send("Loop mode: TRACK")

    @hybrid_command("list")
    async def list(self, ctx: Context):
        if not ctx.guild:
            raise CommandError("Você precisa estar em um canal para usar esse comando")
        if (
            not isinstance(ctx.author, Member)
            or not ctx.author.voice
            or not ctx.author.voice.channel
        ):
            raise CommandError("Você não está em um canal de voz")
        musicDataList = self.musicQueue.get(ctx.guild.id, [])
        await ctx.send(
            f"Fila atual ({len(musicDataList)}): {', '.join(map(lambda m: str(m), musicDataList))}"
        )

    def _after_stop(self, ctx: Context, err: Exception | None):
        loop = asyncio.new_event_loop()
        if err:
            loop.run_until_complete(
                ctx.send(f"Um Erro ocorreu ao tocar a música: {err}")
            )
        loop.run_until_complete(self.playChannel.put(ctx))

    async def playLoop(self):
        while True:
            ctx = await self.playChannel.get()
            if not ctx.guild:
                continue
            if len(self.musicQueue.get(ctx.guild.id, [])) > 0:
                voice = await self.join(ctx)
                if voice.is_playing():
                    continue
                loopMode = self.loopMap.get(ctx.guild.id, LoopMode.OFF)
                if loopMode is LoopMode.TRACK and (
                    currentMusic := self.currentMusic.get(ctx.guild.id)
                ):
                    voice.play(
                        await YoutubeDLSource.from_music_data(currentMusic),
                        after=lambda err: self._after_stop(ctx, err),
                    )
                    continue
                if loopMode is LoopMode.QUEUE and (
                    currentQueue := self.musicQueue.get(ctx.guild.id)
                ):
                    musicData = currentQueue.pop(0)
                    self.currentMusic[ctx.guild.id] = musicData
                    currentQueue.append(musicData)
                    voice.play(
                        await YoutubeDLSource.from_music_data(musicData),
                        after=lambda err: self._after_stop(ctx, err),
                    )
                    continue
                musicData = self.musicQueue.get(ctx.guild.id, []).pop(0)
                self.currentMusic[ctx.guild.id] = musicData
                voice.play(
                    await YoutubeDLSource.from_music_data(musicData),
                    after=lambda err: self._after_stop(ctx, err),
                )

            pass
