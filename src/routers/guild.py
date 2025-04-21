"""Guild Router."""

from __future__ import annotations

from typing import TYPE_CHECKING, cast

from discord.ext.commands import CommandError
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from src.cogs.music import LoopMode, MusicCog
from src.HarpiLib.musicdata.ytmusicdata import YTMusicData
from src.models.canvas import CanvasData, CanvasStorage
from src.models.guild import (
    IGuild,
    IMusic,
    IMusicState,
)
from src.websocket import manager

if TYPE_CHECKING:
    import discord.ext.commands

router = APIRouter(
    responses={404: {"description": "Not found"}},
)

_guilds_cache: list[IGuild] = []
_canvas_storage = CanvasStorage()


@router.get("")
async def get(request: Request) -> list[IGuild]:
    """Retorna uma lista de guildas disponíveis.

    Returns
    -------
    list[IGuild]
        As guildas.

    """
    bot: discord.ext.commands.Bot = request.app.state.bot

    if not _guilds_cache:
        _guilds_cache.extend([
            await IGuild.from_discord_guild(guild)
            async for guild in bot.fetch_guilds()
        ])
    return _guilds_cache


@router.get("/")
async def get_guild(request: Request, idx: str) -> IGuild | None:
    """Retorna uma guilda a partir de um ID.

    Parameters
    ----------
    request : Request
        _description_
    idx : str
        ID da Guilda.

    Returns
    -------
    IGuild
        _description_

    """
    bot: discord.ext.commands.Bot = request.app.state.bot
    guild_id = int(idx)

    discord_guild = bot.get_guild(guild_id)
    return (
        await IGuild.from_discord_guild(discord_guild)
        if discord_guild
        else None
    )


@router.get("/music/list")
async def get_music_list(request: Request, idx: str) -> list[IMusic]:
    """Retorna a lista de músicas de uma Guilda (Incluindo a música atual).

    Parameters
    ----------
    request : Request
        _description_
    idx : str
        Guild ID.

    Returns
    -------
    list[IMusic]
        _description_

    """
    bot: discord.ext.commands.Bot = request.app.state.bot

    music_cog: MusicCog = cast(MusicCog, bot.get_cog("MusicCog"))

    queue = music_cog.music_queue.get(int(idx), []).copy()

    current_music = music_cog.current_music.get(int(idx), None)
    if current_music:
        queue.insert(0, current_music)
    return [IMusic.from_musicdata(music) for music in queue]


@router.get("/state")
async def get_music_state(request: Request, idx: str) -> IMusicState:
    """Get the current music state for a guild.

    Returns
    -------
    IMusicState
        Complete music state.

    """
    guild_id = int(idx)
    bot: discord.ext.commands.Bot = request.app.state.bot
    music_cog: MusicCog = cast(MusicCog, bot.get_cog("MusicCog"))

    return IMusicState.from_music_cog(
        music_cog,
        bot,
        guild_id,
    )


@router.post("/queue")
async def add_to_queue(
    request: Request,
    idx: str,
    url: str,
) -> None:
    """Add a song to the queue.

    Raises
    ------
    HTTPException
        If the URL is empty.
    """
    bot: discord.ext.commands.Bot = request.app.state.bot
    music_cog: MusicCog = cast(MusicCog, bot.get_cog("MusicCog"))
    guild_id = int(idx)

    if len(url) == 0:
        raise HTTPException(
            status_code=400,
            detail="URL não pode ser vazia.",
        )

    try:
        await music_cog.add_music_to_queue(
            guild_id,
            await YTMusicData.from_url(url),
        )
        await music_cog.play_channel.put(guild_id)
    except CommandError as e:
        detail = str(e)
        if "Contexto não encontrado" in detail:
            detail += (
                ". O Harpi deve estar conectado a um canal de voz. "
                "Ou você não selecionou uma guilda."
            )
        raise HTTPException(
            status_code=400,
            detail=detail,
        ) from e


@router.get("/canvas")
async def get_canvas(request: Request, idx: str) -> CanvasData:
    """Obtém os dados do canvas para uma guilda específica.

    Parameters
    ----------
    request : Request
        Requisição FastAPI
    idx : str
        ID da guilda

    Returns
    -------
    CanvasData
        Dados do canvas da guilda
    """
    guild_id = idx
    return _canvas_storage.get_canvas(guild_id)


@router.post("/skip")
async def skip_music(request: Request, idx: str) -> None:
    """Skip the current music."""
    bot: discord.ext.commands.Bot = request.app.state.bot
    music_cog: MusicCog = cast(MusicCog, bot.get_cog("MusicCog"))
    guild_id = int(idx)

    await music_cog.skip_guild(guild_id)
    await manager.broadcast(
        message={
            "entity": ["musics"],
        },
    )


@router.post("/pause")
async def pause_music(request: Request, idx: str) -> None:
    """Pause the current music."""
    bot: discord.ext.commands.Bot = request.app.state.bot
    music_cog: MusicCog = cast(MusicCog, bot.get_cog("MusicCog"))
    guild_id = int(idx)

    await music_cog.pause_guild(guild_id)
    await manager.broadcast(
        message={
            "entity": ["musics"],
        },
    )


@router.post("/resume")
async def resume_music(request: Request, idx: str) -> None:
    """Resume the current music."""
    bot: discord.ext.commands.Bot = request.app.state.bot
    music_cog: MusicCog = cast(MusicCog, bot.get_cog("MusicCog"))
    guild_id = int(idx)

    await music_cog.resume_guild(guild_id)
    await manager.broadcast(
        message={
            "entity": ["musics"],
        },
    )


@router.post("/stop")
async def stop_music(request: Request, idx: str) -> None:
    """Stop the current music."""
    bot: discord.ext.commands.Bot = request.app.state.bot
    music_cog: MusicCog = cast(MusicCog, bot.get_cog("MusicCog"))
    guild_id = int(idx)

    await music_cog.stop_guild(guild_id)
    await manager.broadcast(
        message={
            "entity": ["musics"],
        },
    )


class ILoopRequest(BaseModel):
    """Request to toggle loop"""

    mode: LoopMode


@router.post("/loop")
async def loop_music(
    request: Request,
    idx: str,
    loop_mode: ILoopRequest,
) -> None:
    """Alterna o modo de loop."""

    bot: discord.ext.commands.Bot = request.app.state.bot
    music_cog: MusicCog = cast(MusicCog, bot.get_cog("MusicCog"))

    guild_id = int(idx)

    await music_cog.update_loop_mode(guild_id, loop_mode.mode)


@router.post("/voice/connect")
async def connect_to_voice(
    request: Request,
    idx: str,
    channel_id: str | int,
) -> None:
    """Connect to a voice channel."""

    bot: discord.ext.commands.Bot = request.app.state.bot
    music_cog: MusicCog = cast(MusicCog, bot.get_cog("MusicCog"))

    guild_id = int(idx)
    channel_id = int(channel_id)

    await music_cog.connect_to_voice(guild_id, channel_id)
