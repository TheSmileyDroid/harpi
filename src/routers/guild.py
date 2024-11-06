"""Guild Router."""

from __future__ import annotations

from typing import TYPE_CHECKING

from fastapi import APIRouter, Request
from pydantic import BaseModel

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

    id: int
    name: str
    description: str | None
    approximate_member_count: int


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


@router.get("/{idx}")
async def get_guild(request: Request, idx: int) -> IGuild:
    """Retorna uma guilda a partir de um ID.

    Parameters
    ----------
    request : Request
        _description_
    idx : int
        ID da Guilda.

    Returns
    -------
    IGuild
        _description_

    """
    bot: discord.ext.commands.Bot = request.app.state.bot

    return bot.get_guild(idx)


@router.get("/{idx}/music/list")
async def get_music_list(request: Request, idx: int) -> list[IMusic]:
    """Retorna a lista de músicas de uma Guilda (Incluindo a música atual).

    Parameters
    ----------
    request : Request
        _description_
    idx : int
        Guild ID.

    Returns
    -------
    list[IMusic]
        _description_

    """
    bot: discord.ext.commands.Bot = request.app.state.bot

    music_cog: MusicCog = bot.get_cog("MusicCog")

    if music_cog.music_queue.get(idx) is None:
        return []

    queue = music_cog.music_queue.get(idx).copy()
    queue.append(music_cog.current_music.get(idx))
    return queue
