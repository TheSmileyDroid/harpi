"""Guild Router."""

from __future__ import annotations

from typing import TYPE_CHECKING

from fastapi import APIRouter, Request
from pydantic import BaseModel, ConfigDict

from src.cogs.music import LoopMode

if TYPE_CHECKING:
    import discord.ext.commands

    from src.cogs.music import MusicCog

router = APIRouter(
    prefix="/guilds",
    tags=["guild"],
    responses={404: {"description": "Not found"}},
)


class IMusic(BaseModel):
    """Music data model."""

    title: str
    url: str
    thumbnail: str | None


class IGuild(BaseModel):
    """Guild model."""

    model_config = ConfigDict(coerce_numbers_to_str=True)

    id: str
    name: str
    description: str | None
    approximate_member_count: int


class IMusicState(BaseModel):
    """Model for sending all the Music state of a guild."""

    queue: list[IMusic]
    loop_mode: LoopMode


@router.get("")
async def get(request: Request) -> list[IGuild]:
    """Retorna uma lista de guildas disponíveis.

    Returns
    -------
    list[IGuild]
        As guildas.

    """
    bot: discord.ext.commands.Bot = request.app.state.bot

    return [guild async for guild in bot.fetch_guilds(limit=150)]


@router.get("/")
async def get_guild(request: Request, idx: str) -> IGuild:
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

    return bot.get_guild(guild_id)


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

    music_cog: MusicCog = bot.get_cog("MusicCog")

    queue = music_cog.music_queue.get(idx, []).copy()

    current_music = music_cog.current_music.get(idx, None)
    if current_music:
        queue.insert(0, current_music)
    return queue


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
    music_cog: MusicCog = bot.get_cog("MusicCog")

    active_track = music_cog.current_music.get(guild_id, None)
    music_queue = music_cog.music_queue.get(guild_id, [])
    result_queue = []
    if active_track:
        music_queue.insert(0, active_track)
    for music in music_queue:
        result_queue.append(  # noqa: PERF401
            IMusic(
                title=music.title,
                url=music.url,
                thumbnail=music.thumbnail,
            ),
        )
    return IMusicState(
        queue=result_queue,
        loop_mode=music_cog.loop_map.get(guild_id, LoopMode.OFF),
    )


@router.post("/queue")
async def add_to_queue(
    request: Request,
    idx: str,
    url: str,
) -> IMusicState:
    """Add a song to the queue."""
    bot: discord.ext.commands.Bot = request.app.state.bot
    music_cog: MusicCog = bot.get_cog("MusicCog")
    guild_id = int(idx)

    music_cog.add_music(url, idx=guild_id)
