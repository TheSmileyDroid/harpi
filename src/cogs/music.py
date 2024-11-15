"""Módulo responsável por tocar músicas."""

from __future__ import annotations

import asyncio
import enum
from asyncio import sleep
from asyncio.queues import Queue
from functools import partial
from typing import cast

import discord
import discord.ext
import discord.ext.commands
from discord import ClientException, Member
from discord.app_commands import describe
from discord.ext.commands import Cog, CommandError, Context, hybrid_command
from discord.voice_client import VoiceClient

from src.HarpiLib.musicdata.ytmusicdata import (
    AudioSourceTracked,
    YoutubeDLSource,
    YTMusicData,
)
from src.HarpiLib.nested import get_nested_attr
from src.websocket import manager


class LoopMode(enum.Enum):
    """Enum que representa o modo de loop."""

    OFF = 0
    TRACK = 1
    QUEUE = 2


idx_count = 0


class MusicCog(Cog):
    """Cog responsável por tocar músicas."""

    def __init__(self, bot: discord.ext.commands.bot.Bot) -> None:
        """Inicializa o cog."""
        super().__init__()

        self.music_queue: dict[int, list[YTMusicData]] = {}
        self.loop_map: dict[int, LoopMode] = {}
        self.play_channel: Queue[Context] = Queue()
        self.current_music: dict[int, YTMusicData | None] = {}
        self.default_ctx: dict[int, Context] = {}
        self.tasks = []
        self.bot = bot
        for _i in range(3):
            task = asyncio.create_task(self.play_loop())
            self.tasks.append(task)

    @hybrid_command("join")
    async def join(self, ctx: Context) -> VoiceClient:
        """Entra no canal de voz do usuário.

        Args:
             ctx (Context): Contexto do comando.

        Returns:
             VoiceClient: Cliente de voz do usuário.

        Raises:
             CommandError: Se o usuário não estiver em um canal de voz.

        """
        self.default_ctx[get_nested_attr(ctx.guild, "id", -1)] = ctx
        if (
            not isinstance(ctx.author, Member)
            or not ctx.author.voice
            or not ctx.author.voice.channel
        ):
            raise CommandError("Contexto não encontrado")
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
        self.default_ctx[get_nested_attr(ctx.guild, "id", -1)] = ctx
        await self.add_music(link, ctx)

    async def notify_queue_update(self) -> None:
        """Notify frontend clients that queue has changed."""

        await manager.broadcast({
            "entity": ["musics"],
        })

    async def add_music(
        self,
        link: str,
        ctx: Context | None = None,
        idx: int = -1,
    ) -> None:
        """Add music to the queue.

        Parameters
        ----------
        link : str
            Music link.
        ctx : Context, optional
            Context of the command, by default None
        idx : int, optional
            Index of the music to be added, by default -1

        Raises
        ------
        CommandError
            If the context is not found

        """
        if ctx is None:
            ctx = self.default_ctx.get(idx, None)
        if ctx is None:
            raise CommandError("Contexto não encontrado")

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
            await self.notify_queue_update()
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
            raise CommandError("Contexto não encontrado")
        guild_id = ctx.guild.id
        await self.stop_guild(guild_id)
        await ctx.send("Música parada")

    async def stop_guild(self, guild_id: int) -> None:
        self.music_queue[guild_id] = []
        self.current_music[guild_id] = None
        voice = self.get_voice_client(guild_id)
        if voice:
            voice.stop()
        await self.notify_queue_update()

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
        guild_id = ctx.guild.id
        await self.skip_guild(guild_id)
        await ctx.send("Música pulada")

    async def skip_guild(self, guild_id: int) -> None:
        is_queue_loop = (
            self.loop_map.get(guild_id, LoopMode.OFF) is LoopMode.QUEUE
        )
        if is_queue_loop and (
            current_music := self.current_music.get(guild_id)
        ):
            self.music_queue.get(guild_id, []).append(current_music)
        self.current_music[guild_id] = None
        voice = self.get_voice_client(guild_id)
        if voice:
            voice.stop()
        await self.notify_queue_update()

    @hybrid_command("pause")
    async def pause(self, ctx: Context) -> None:
        """Pausa a música atual."""
        await ctx.typing()
        if not ctx.guild:
            return
        guild_id = ctx.guild.id
        await self.pause_guild(guild_id)
        await ctx.send("Música pausada")
        await self.notify_queue_update()

    async def pause_guild(self, guild_id: int) -> None:
        voice = self.get_voice_client(guild_id)
        if voice:
            voice.pause()
        else:
            raise CommandError("Não foi possível pausar a música")

    @hybrid_command("resume")
    async def resume(self, ctx: Context) -> None:
        """Retoma a música atual."""
        await ctx.typing()
        if not ctx.guild:
            return
        guild_id = ctx.guild.id
        await self.resume_guild(guild_id)
        await ctx.send("Música retomada")
        await self.notify_queue_update()

    async def resume_guild(self, guild_id: int) -> None:
        voice = self.get_voice_client(guild_id)
        if voice:
            voice.resume()
        else:
            raise CommandError("Não foi possível retomar a música")

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
        elif self.loop_map.get(ctx.guild.id, LoopMode.OFF) is not LoopMode.OFF:
            self.loop_map[ctx.guild.id] = LoopMode.OFF
            await ctx.send("Loop mode: OFF")
        else:
            self.loop_map[ctx.guild.id] = LoopMode.TRACK
            await ctx.send("Loop mode: TRACK")
        await self.notify_queue_update()

    @hybrid_command("list", aliases=["queue", "q"])
    async def list_musics(self, ctx: Context) -> None:
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
        await self.notify_queue_update()

    def _after_stop(self, ctx: Context, err: Exception | None) -> None:
        """After stop callback.

        Args:
            ctx (Context): Contexto do comando.
            err (Exception | None): Erro ocorrido ao tocar a música.

        """
        loop = asyncio.new_event_loop()
        if err:
            loop.run_until_complete(
                ctx.send(f"Um Erro ocorreu ao tocar a música: {err}"),
            )
        loop.run_until_complete(self.play_channel.put(ctx))

    async def play_loop(self) -> None:
        """Play loop."""
        global idx_count  # noqa: PLW0602
        idx = ++idx_count  # noqa: B002
        ctx = None

        try:
            while True:
                ctx = await self.play_channel.get()
                guild_id = get_nested_attr(ctx.guild, "id", -1)
                voice = await self.join(ctx)
                await sleep(0.05)
                loop_mode = self.loop_map.get(guild_id, LoopMode.OFF)
                current_music = self.current_music.get(guild_id)
                queue = self.music_queue.get(guild_id, [])

                if voice.is_playing():
                    await self.notify_queue_update()
                    continue

                music_to_play = self.select_music_to_play(
                    loop_mode,
                    current_music,
                    queue,
                )

                self.current_music[guild_id] = music_to_play

                if music_to_play:
                    voice.play(
                        AudioSourceTracked(
                            await YoutubeDLSource.from_music_data(
                                music_to_play,
                            ),
                        ),
                        after=partial(
                            lambda err, ctx_temp: self._after_stop(
                                ctx_temp,
                                err,
                            ),
                            ctx_temp=ctx,
                        ),
                    )
                await sleep(0.05)
                await self.notify_queue_update()

        except ClientException as e:
            if ctx:
                await ctx.send(f"Erro ao tocar a música no worker {idx}: {e}")

            task = asyncio.create_task(self.play_loop())
            self.tasks.append(task)
        except TypeError as e:
            if ctx:
                await ctx.send(
                    f"Problema ao tocar a música no worker {idx}: {e}",
                )
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
            else:
                music_to_play = None
        elif queue and len(queue) > 0:
            music_to_play = queue.pop(0)
        else:
            music_to_play = None
        return music_to_play

    def get_voice_client(self, guild_id: int) -> VoiceClient | None:
        """Get voice client.

        Args:
            guild_id (int): Guild ID.

        Returns:
            VoiceClient | None: Voice client.

        """

        bot = self.bot
        if bot:
            guild = bot.get_guild(guild_id)
            if guild:
                return cast(VoiceClient, guild.voice_client)
        return None
