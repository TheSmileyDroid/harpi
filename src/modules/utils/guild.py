from discord.ext import commands
import discord
from src.modules.utils.aichat import AIChat
from src.modules.utils.musicdata import MusicData


class GuildsData:

    def __init__(self) -> None:
        self._queue: dict[int, list[MusicData]] = {}
        self._chat: dict[int, AIChat] = {}
        self._is_looping: dict[int, bool] = {}
        self._volume: dict[int, float] = {}
        self._skip_flag: dict[int, bool] = {}

    def chat(self, ctx) -> AIChat:
        guild_id = guild(ctx).id
        return self._chat.setdefault(guild_id, AIChat())

    def queue(self, ctx) -> list:
        guild_id = guild(ctx).id
        return self._queue.setdefault(guild_id, [])

    def is_looping(self, ctx) -> bool:
        guild_id = guild(ctx).id
        return self._is_looping.setdefault(guild_id, False)

    def set_looping(self, ctx, value: bool):
        guild_id = guild(ctx).id
        self._is_looping[guild_id] = value

    def volume(self, ctx) -> float:
        guild_id = guild(ctx).id
        return self._volume.setdefault(guild_id, 0.3)

    def set_volume(self, ctx, value: float):
        guild_id = guild(ctx).id
        self._volume[guild_id] = value

    def skip_flag(self, ctx) -> bool:
        guild_id = guild(ctx).id
        return self._skip_flag.setdefault(guild_id, False)

    def set_skip_flag(self, ctx, value: bool):
        guild_id = guild(ctx).id
        self._skip_flag[guild_id] = value


global guild_data
guild_data = GuildsData()


def guild(ctx: commands.Context) -> discord.Guild:
    if ctx.guild is None:
        raise commands.NoPrivateMessage(
            'Este comando não pode ser usado em DMs')
    return ctx.guild
