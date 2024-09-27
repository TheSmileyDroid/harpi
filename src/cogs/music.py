"""Módulo responsável por tocar músicas."""

from __future__ import annotations

import asyncio
import enum
from asyncio import sleep
from asyncio.queues import Queue

from discord import Member
from discord.app_commands import describe
from discord.ext.commands import Cog, CommandError, Context, hybrid_command
from discord.voice_client import VoiceClient

from src.musicdata.ytmusicdata import YoutubeDLSource, YTMusicData


class LoopMode(enum.Enum):
    """Enum que representa o modo de loop."""

    OFF = 0
    TRACK = 1
    QUEUE = 2


class MusicCog(Cog):
    """Cog responsável por tocar músicas."""

    def __init__(self) -> None:
        """Inicializa o cog."""
        super().__init__()

        self.music_queue: dict[int, list[YTMusicData]] = {}
        self.loopMap: dict[int, LoopMode] = {}
        self.playChannel: Queue[Context] = Queue()
        self.currentMusic: dict[int, YTMusicData | None] = {}
        tasks = []
        for _i in range(3):
            task = asyncio.create_task(self.playLoop())
            tasks.append(task)

    @staticmethod
    async def join(ctx: Context) -> VoiceClient:
        """Entra no canal de voz do usuário.

        Args:
             ctx (Context): Contexto do comando.

        Returns:
             VoiceClient: Cliente de voz do usuário.

        Raises:
             CommandError: Se o usuário não estiver em um canal de voz.

        """
        if (
            not isinstance(ctx.author, Member)
            or not ctx.author.voice
            or not ctx.author.voice.channel
        ):
            raise CommandError
        if ctx.voice_client is not None and isinstance(
            ctx.voice_client,
            VoiceClient,
        ):
            voice_channel = ctx.author.voice.channel
            await ctx.voice_client.move_to(voice_channel)
            return ctx.voice_client
        return await ctx.author.voice.channel.connect()

    @hybrid_command("play")
    @describe(link="Link da música a ser tocada")
    async def play(self, ctx: Context, *, link: str) -> None:
        """Toca uma música.

        Arguments:
            ctx (Context): Contexto do comando.
            link (str): Link da música a ser tocada.

        """
        await ctx.typing()
        if ctx.guild:
            music_data_list = await YTMusicData.from_url(link)
            queue = self.music_queue.get(ctx.guild.id) or []
            for music_data in music_data_list:
                queue.append(music_data)
            self.music_queue[ctx.guild.id] = queue
            await self.playChannel.put(ctx)
            musics = ", ".join(m.get_title() for m in music_data_list)
            await ctx.send(f"Adicionando à fila: {musics}")
        else:
            await ctx.send("Você não está numa guilda")

    @hybrid_command("stop")
    async def stop(self, ctx: Context) -> None:
        await ctx.typing()
        if not ctx.guild:
            raise CommandError(
                "Você precisa estar em um canal para usar esse comando",
            )
        voice = await self.join(ctx)
        self.music_queue[ctx.guild.id] = []
        self.currentMusic[ctx.guild.id] = None
        voice.stop()
        await ctx.send("Música parada")

    @hybrid_command("skip")
    async def skip(self, ctx: Context):
        await ctx.typing()
        if not ctx.guild:
            raise CommandError(
                "Você precisa estar em um canal para usar esse comando",
            )
        voice = await self.join(ctx)
        if self.loopMap.get(ctx.guild.id, LoopMode.OFF) is LoopMode.QUEUE:
            if currentMusic := self.currentMusic.get(ctx.guild.id):
                self.music_queue.get(ctx.guild.id, []).append(currentMusic)
        self.currentMusic[ctx.guild.id] = None
        await ctx.send("Música pulada")
        musicQueue = self.music_queue.get(ctx.guild.id, [])
        print(musicQueue)
        if len(musicQueue) > 0 and (nextMusic := musicQueue[0]):
            await ctx.send(
                f"Tocando a próxima música da fila: **{nextMusic.get_title()}**",
            )
        else:
            await ctx.send("Fila vazia")
        voice.stop()

    @hybrid_command("pause")
    async def pause(self, ctx: Context):
        await ctx.typing()
        voice = await self.join(ctx)
        voice.pause()
        await ctx.send("Pausado")

    @hybrid_command("resume")
    async def resume(self, ctx: Context):
        await ctx.typing()
        voice = await self.join(ctx)
        voice.resume()
        await ctx.send("Resumido")

    @hybrid_command("loop")
    @describe(mode="Loop mode")
    async def loop(self, ctx: Context, mode: str | None):
        await ctx.typing()
        if not ctx.guild:
            raise CommandError(
                "Você precisa estar em um canal para usar esse comando",
            )
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
        elif self.loopMap.get(ctx.guild.id, LoopMode.OFF) is not LoopMode.OFF:
            self.loopMap[ctx.guild.id] = LoopMode.OFF
            print("Loop mode: OFF")
            await ctx.send("Loop mode: OFF")
        else:
            self.loopMap[ctx.guild.id] = LoopMode.TRACK
            print("Loop mode: TRACK")
            await ctx.send("Loop mode: TRACK")

    @hybrid_command("list")
    async def list(self, ctx: Context):
        await ctx.typing()
        if not ctx.guild:
            raise CommandError(
                "Você precisa estar em um canal para usar esse comando",
            )
        if (
            not isinstance(ctx.author, Member)
            or not ctx.author.voice
            or not ctx.author.voice.channel
        ):
            raise CommandError("Você não está em um canal de voz")
        music_data_list = self.music_queue.get(ctx.guild.id, [])
        currentMusicStr = (
            f"**{currentMusic.get_title()}**"
            if (currentMusic := self.currentMusic.get(ctx.guild.id))
            else "Nenhuma música sendo tocada"
        )
        list = "\n ".join(
            map(lambda m: f"**{m.get_title()}**", music_data_list),
        )
        await ctx.send(
            f"{currentMusicStr}\nFila atual ({len(music_data_list)}): \n{list}",
        )

    def _after_stop(self, ctx: Context, err: Exception | None):
        loop = asyncio.new_event_loop()
        if err:
            loop.run_until_complete(
                ctx.send(f"Um Erro ocorreu ao tocar a música: {err}"),
            )
        loop.run_until_complete(self.playChannel.put(ctx))

    async def playLoop(self):
        while True:
            ctx = await self.playChannel.get()
            if not ctx.guild:
                continue

            guild_id = ctx.guild.id
            voice = await self.join(ctx)
            await sleep(0.5)

            if voice.is_playing():
                continue

            loopMode = self.loopMap.get(guild_id, LoopMode.OFF)
            currentMusic = self.currentMusic.get(guild_id)
            queue = self.music_queue.get(guild_id, [])

            if loopMode is LoopMode.TRACK and currentMusic:
                music_to_play = currentMusic
            elif loopMode is LoopMode.QUEUE:
                if queue and len(queue) > 0:
                    music_to_play = queue.pop(0)
                    if currentMusic:
                        queue.append(currentMusic)
                elif currentMusic:
                    music_to_play = currentMusic
                    queue.append(currentMusic)
                else:
                    music_to_play = None
            elif queue and len(queue) > 0:
                music_to_play = queue.pop(0)
            else:
                music_to_play = None

            if music_to_play:
                self.currentMusic[guild_id] = music_to_play
                voice.play(
                    await YoutubeDLSource.from_music_data(music_to_play),
                    after=lambda err: self._after_stop(ctx, err),
                )
            else:
                self.currentMusic[guild_id] = None
                print("No music data in queue or current music")
