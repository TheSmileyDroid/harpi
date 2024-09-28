"""Módulo responsável por tocar músicas."""

from __future__ import annotations

import asyncio
import enum
from asyncio import sleep
from asyncio.queues import Queue
from functools import partial
from typing import NoReturn

from discord import ClientException, Member
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
        self.loop_map: dict[int, LoopMode] = {}
        self.play_channel: Queue[Context] = Queue()
        self.current_music: dict[int, YTMusicData | None] = {}
        self.tasks = []
        for _i in range(3):
            task = asyncio.create_task(self.play_loop())
            self.tasks.append(task)

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
            await self.play_channel.put(ctx)
            musics = ", ".join(m.get_title() for m in music_data_list)
            await ctx.send(f"Adicionando à fila: {musics}")
        else:
            await ctx.send("Você não está numa guilda")

    @hybrid_command("stop")
    async def stop(self, ctx: Context) -> None:
        """Para a música atual.

        Args:
            ctx (Context): Contexto do comando.

        Raises:
            CommandError: Se o usuário não estiver em um canal de voz.

        """
        await ctx.typing()
        if not ctx.guild:
            raise CommandError
        voice = await self.join(ctx)
        self.music_queue[ctx.guild.id] = []
        self.current_music[ctx.guild.id] = None
        voice.stop()
        await ctx.send("Música parada")

    @hybrid_command("skip")
    async def skip(self, ctx: Context) -> None:
        """Pula a música atual.

        Args:
            ctx (Context): Contexto do comando.

        Raises:
            CommandError: Se o usuário não estiver em um canal de voz.

        """
        await ctx.typing()
        if not ctx.guild:
            raise CommandError
        voice = await self.join(ctx)
        is_queue_loop = (
            self.loop_map.get(ctx.guild.id, LoopMode.OFF) is LoopMode.QUEUE
        )
        if is_queue_loop and (
            current_music := self.current_music.get(ctx.guild.id)
        ):
            self.music_queue.get(ctx.guild.id, []).append(current_music)
        self.current_music[ctx.guild.id] = None
        await ctx.send("Música pulada")
        music_queue = self.music_queue.get(ctx.guild.id, [])
        if len(music_queue) > 0 and (next_music := music_queue[0]):
            title = next_music.get_title()
            await ctx.send(
                f"Tocando a próxima música da fila: **{title}**",
            )
        else:
            await ctx.send("Fila vazia")
        voice.stop()

    @hybrid_command("pause")
    async def pause(self, ctx: Context) -> None:
        """Pause the current music.

        Args:
            ctx (Context): Contexto do comando.

        """
        await ctx.typing()
        voice = await self.join(ctx)
        voice.pause()
        await ctx.send("Pausado")

    @hybrid_command("resume")
    async def resume(self, ctx: Context) -> None:
        """Resume the current music.

        Args:
            ctx (Context): Contexto do comando.

        """
        await ctx.typing()
        voice = await self.join(ctx)
        voice.resume()
        await ctx.send("Resumido")

    @hybrid_command("loop")
    @describe(mode="Loop mode")
    async def loop(self, ctx: Context, mode: str | None) -> None:
        """Loop mode command [off, track, queue].

        Args:
            ctx (Context): Contexto do comando.
            mode (str | None): Loop mode [off, track, queue].

        Raises:
            CommandError: If the user is not in a voice channel.

        """
        await ctx.typing()
        if not ctx.guild:
            raise CommandError
        if mode in {"off", "false", "0", "no", "n"}:
            self.loop_map[ctx.guild.id] = LoopMode.OFF
            await ctx.send("Loop mode: OFF")
        elif mode in {"track", "true", "1", "yes", "y", "musica"}:
            self.loop_map[ctx.guild.id] = LoopMode.TRACK
            await ctx.send("Loop mode: TRACK")
        elif mode in {"queue", "q", "fila", "f", "lista", "l"}:
            self.loop_map[ctx.guild.id] = LoopMode.QUEUE
            await ctx.send("Loop mode: QUEUE")
        elif (
            self.loop_map.get(ctx.guild.id, LoopMode.OFF) is not LoopMode.OFF
        ):
            self.loop_map[ctx.guild.id] = LoopMode.OFF
            await ctx.send("Loop mode: OFF")
        else:
            self.loop_map[ctx.guild.id] = LoopMode.TRACK
            await ctx.send("Loop mode: TRACK")

    @hybrid_command("list")
    async def list(self, ctx: Context) -> None:
        """List the current music queue.

        Args:
            ctx (Context): Contexto do comando.

        Raises:
            CommandError: If the user is not in a voice channel.
            CommandError: If the user is not in a guild.

        """
        await ctx.typing()
        if not ctx.guild:
            raise CommandError
        if (
            not isinstance(ctx.author, Member)
            or not ctx.author.voice
            or not ctx.author.voice.channel
        ):
            raise CommandError
        music_data_list = self.music_queue.get(ctx.guild.id, [])
        current_music_str = (
            f"**{current_music.get_title()}**"
            if (current_music := self.current_music.get(ctx.guild.id))
            else "Nenhuma música sendo tocada"
        )
        list_str = "\n ".join(
            (f"**{m.get_title()}**" for m in music_data_list),
        )
        await ctx.send(
            f"{current_music_str}\nFila atual ({len(music_data_list)}): \n{list_str}",  # noqa: E501
        )

    def _after_stop(self, ctx: Context, err: Exception | None) -> None:
        """After stop callback.

        Args:
            ctx (Context): Contexto do comando.
            err (Exception | None): Erro ocorrido ao tocar a música.

        """
        self.current_music[ctx.guild.id] = None
        loop = asyncio.new_event_loop()
        if err:
            loop.run_until_complete(
                ctx.send(f"Um Erro ocorreu ao tocar a música: {err}"),
            )
        loop.run_until_complete(self.play_channel.put(ctx))

    async def play_loop(self) -> NoReturn:
        """Play loop."""
        try:
            while True:
                ctx = await self.play_channel.get()
                guild_id = ctx.guild.id
                voice = await self.join(ctx)
                await sleep(0.5)
                loop_mode = self.loop_map.get(guild_id, LoopMode.OFF)
                current_music = self.current_music.get(guild_id)
                queue = self.music_queue.get(guild_id, [])

                if current_music is not None:
                    title = self.current_music[guild_id].get_title()
                    await ctx.send(
                        f"Música em andamento: {title}",
                    )
                    continue

                music_to_play = self.select_music_to_play(
                    loop_mode,
                    current_music,
                    queue,
                )

                if music_to_play:
                    self.current_music[guild_id] = music_to_play
                    voice.play(
                        await YoutubeDLSource.from_music_data(music_to_play),
                        after=partial(
                            lambda err, ctx: self._after_stop(ctx, err),
                            ctx=ctx,
                        ),
                    )

        except ClientException as e:
            await ctx.send(f"Erro ao tocar a música: {e}")
            task = asyncio.create_task(self.play_loop())
            self.tasks.append(task)
        except TypeError as e:
            await ctx.send(f"Problema ao tocar a música: {e}")
            task = asyncio.create_task(self.play_loop())
            self.tasks.append(task)

    @staticmethod
    def select_music_to_play(
        loop_mode: LoopMode,
        current_music: YTMusicData | None,
        queue: list[YTMusicData],
    ) -> YTMusicData | None:
        """Select music to play.

        Args:
            loop_mode (LoopMode): Mode of loop.
            current_music (YTMusicData | None): Current music.
            queue (list[YTMusicData]): Queue of music.

        Returns:
            YTMusicData | None: Music to play.

        """
        if loop_mode is LoopMode.TRACK and current_music:
            music_to_play = current_music
        elif loop_mode is LoopMode.QUEUE:
            if queue and len(queue) > 0:
                music_to_play = queue.pop(0)
                if current_music:
                    queue.append(current_music)
            elif current_music:
                music_to_play = current_music
                queue.append(current_music)
            else:
                music_to_play = None
        elif queue and len(queue) > 0:
            music_to_play = queue.pop(0)
        else:
            music_to_play = None
        return music_to_play
