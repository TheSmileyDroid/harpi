"""Guild Router."""

from __future__ import annotations

from typing import cast

import discord.ext.commands
from discord import VoiceClient
from discord.ext.commands import CommandError
from fastapi import APIRouter, HTTPException, Request

from src.cogs.music import LoopMode, MusicCog
from src.models.guild import (
    AudioSourceTrackedProtocol,
    IGuild,
    IMusic,
    IMusicState,
)

router = APIRouter(
    prefix="/guilds",
    tags=["guild"],
    responses={404: {"description": "Not found"}},
)


@router.get("")
async def get(request: Request) -> list[IGuild]:
    """Retorna uma lista de guildas disponíveis.

    Returns
    -------
    list[IGuild]
        As guildas.

    """
    bot: discord.ext.commands.Bot = request.app.state.bot

    return [IGuild.from_discord_guild(guild) for guild in bot.guilds]


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
    return IGuild.from_discord_guild(discord_guild) if discord_guild else None


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

    active_track = music_cog.current_music.get(guild_id, None)
    music_queue = music_cog.music_queue.get(guild_id, []).copy()
    result_queue = []
    if active_track:
        music_queue.insert(0, active_track)
    for music in music_queue:
        result_queue.append(  # noqa: PERF401
            IMusic.from_musicdata(
                music,
            ),
        )
    progress = 0
    for _voice_client in bot.voice_clients:
        voice_client = cast(VoiceClient, _voice_client)
        if voice_client.guild.id == guild_id:
            if not voice_client.source:
                continue
            source = cast(AudioSourceTrackedProtocol, voice_client.source)
            progress = source.progress
            break
    return IMusicState(
        queue=result_queue,
        loop_mode=music_cog.loop_map.get(guild_id, LoopMode.OFF),
        progress=progress,
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
        await music_cog.add_music(url, idx=guild_id)
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
