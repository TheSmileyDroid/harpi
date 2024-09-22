import enum
from asyncio import sleep
from asyncio.queues import Queue
from typing import Optional

from discord import Member
from discord.app_commands import describe
from discord.ext.commands import Bot, Cog, CommandError, Context, hybrid_command
from discord.ext.commands.bot import asyncio
from discord.voice_client import VoiceClient

from src.res.utils.ytmusicdata import YoutubeDLSource, YTMusicData


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
            return ctx.voice_client  # type: ignore
        return await ctx.author.voice.channel.connect()

    @hybrid_command("play")
    @describe(link="Link da música a ser tocada")
    async def play(self, ctx: Context, *, link: str):
        await ctx.typing()
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
        await ctx.typing()
        if not ctx.guild:
            raise CommandError("Você precisa estar em um canal para usar esse comando")
        voice = await self.join(ctx)
        self.musicQueue[ctx.guild.id] = []
        self.currentMusic[ctx.guild.id] = None
        voice.stop()
        await ctx.send("Música parada")

    @hybrid_command("skip")
    async def skip(self, ctx: Context):
        await ctx.typing()
        if not ctx.guild:
            raise CommandError("Você precisa estar em um canal para usar esse comando")
        voice = await self.join(ctx)
        if self.loopMap.get(ctx.guild.id, LoopMode.OFF) is LoopMode.QUEUE:
            if currentMusic := self.currentMusic.get(ctx.guild.id):
                self.musicQueue.get(ctx.guild.id, []).append(currentMusic)
        self.currentMusic[ctx.guild.id] = None
        await ctx.send("Música pulada")
        musicQueue = self.musicQueue.get(ctx.guild.id, [])
        print(musicQueue)
        if len(musicQueue) > 0 and (nextMusic := musicQueue[0]):
            await ctx.send(
                f"Tocando a próxima música da fila: **{nextMusic.get_title()}**"
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
    async def loop(self, ctx: Context, mode: Optional[str]):
        await ctx.typing()
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
        await ctx.typing()
        if not ctx.guild:
            raise CommandError("Você precisa estar em um canal para usar esse comando")
        if (
            not isinstance(ctx.author, Member)
            or not ctx.author.voice
            or not ctx.author.voice.channel
        ):
            raise CommandError("Você não está em um canal de voz")
        musicDataList = self.musicQueue.get(ctx.guild.id, [])
        currentMusicStr = (
            f"**{currentMusic.get_title()}**"
            if (currentMusic := self.currentMusic.get(ctx.guild.id))
            else "Nenhuma música sendo tocada"
        )
        list = "\n ".join(map(lambda m: f"**{m.get_title()}**", musicDataList))
        await ctx.send(
            f"{currentMusicStr}\nFila atual ({len(musicDataList)}): \n{list}"
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

            guild_id = ctx.guild.id
            voice = await self.join(ctx)
            await sleep(0.5)

            if voice.is_playing():
                continue

            loopMode = self.loopMap.get(guild_id, LoopMode.OFF)
            currentMusic = self.currentMusic.get(guild_id)
            queue = self.musicQueue.get(guild_id, [])

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
