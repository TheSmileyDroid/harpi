import discord
from discord.ext import commands

from src.res.utils.aichat import AIChat

from ..interfaces.iguildsdata import IGuildsData
from ..interfaces.imusicqueue import IMusicQueue
from .musicqueue import MusicQueue


def guild(ctx: commands.Context) -> discord.Guild:
    if ctx.guild is None:
        raise commands.NoPrivateMessage(
            "Este comando não pode ser usado em DMs"
        )
    return ctx.guild


def guild_id(ctx: commands.Context, accepts_dm: bool = False) -> int:
    if ctx.guild is None:
        if accepts_dm:
            return ctx.author.id
        raise commands.NoPrivateMessage(
            "Este comando não pode ser usado em DMs"
        )
    return ctx.guild.id


class InternalGuildsData(IGuildsData):
    def __init__(self) -> None:
        self._queue: dict[int, IMusicQueue] = {}
        self._chat: dict[int, AIChat] = {}
        self._is_looping: dict[int, bool] = {}
        self._volume: dict[int, float] = {}
        self._skip_flag: dict[int, bool] = {}
        self._custom_data: dict[int, dict[str, str]] = {}

    def chat(self, ctx: commands.Context) -> AIChat:
        id = guild_id(ctx, accepts_dm=True)
        return self._chat.setdefault(id, AIChat())

    def queue(self, ctx: commands.Context) -> IMusicQueue:
        guild_id = guild(ctx).id
        return self._queue.setdefault(guild_id, MusicQueue())

    def is_looping(self, ctx: commands.Context) -> bool:
        guild_id = guild(ctx).id
        return self._is_looping.setdefault(guild_id, False)

    def set_looping(self, ctx: commands.Context, value: bool):
        guild_id = guild(ctx).id
        self._is_looping[guild_id] = value

    def volume(self, ctx: commands.Context) -> float:
        guild_id = guild(ctx).id
        return self._volume.setdefault(guild_id, 0.3)

    def set_volume(self, ctx: commands.Context, value: float):
        guild_id = guild(ctx).id
        self._volume[guild_id] = value

    def skip_flag(self, ctx: commands.Context) -> bool:
        guild_id = guild(ctx).id
        return self._skip_flag.setdefault(guild_id, False)

    def set_skip_flag(self, ctx: commands.Context, value: bool):
        guild_id = guild(ctx).id
        self._skip_flag[guild_id] = value

    def set_queue(self, ctx: commands.Context, value: IMusicQueue):
        guild_id = guild(ctx).id
        self._queue[guild_id] = value

    def add_custom_data(
        self, ctx: commands.Context, key: str, value: str
    ) -> None:
        guild_id = guild(ctx).id
        self._custom_data.setdefault(guild_id, dict()).update({key: value})

    def get_custom_data(self, ctx: commands.Context, key: str) -> str:
        guild_id = guild(ctx).id
        return self._custom_data.setdefault(guild_id, dict()).get(key, "")


global guild_data
guild_data: IGuildsData = InternalGuildsData()

global guild_ids
guild_ids: dict[int, str] = dict()
