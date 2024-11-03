"""Guild Router."""

from __future__ import annotations

from typing import TYPE_CHECKING

from fastapi import APIRouter, Request
from pydantic import BaseModel

if TYPE_CHECKING:
    import discord.ext.commands

router = APIRouter(
    prefix="/guilds",
    tags=["guild"],
    responses={404: {"description": "Not found"}},
)


class Guild(BaseModel):
    """Guild model."""

    id: int
    name: str
    description: str | None
    approximate_member_count: int


@router.get("")
async def get(request: Request) -> list[Guild]:
    """Retorna uma lista de guildas disponíveis.

    Returns
    -------
    list[Guild]
        As guildas.

    """
    bot: discord.ext.commands.Bot = request.app.state.bot
    return [guild async for guild in bot.fetch_guilds(limit=150)]
