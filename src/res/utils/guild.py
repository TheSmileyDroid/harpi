from abc import ABC, abstractmethod
import random
from discord.ext import commands
import discord
from src.res.utils.aichat import AIChat
from src.res.utils.musicdata import MusicData


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


class GuildsData(ABC):
    @abstractmethod
    def chat(self, ctx: commands.Context) -> AIChat:
        pass

    @abstractmethod
    def queue(self, ctx: commands.Context) -> list[MusicData]:
        pass

    @abstractmethod
    def is_looping(self, ctx: commands.Context) -> bool:
        pass

    @abstractmethod
    def set_looping(self, ctx: commands.Context, value: bool):
        pass

    @abstractmethod
    def volume(self, ctx: commands.Context) -> float:
        pass

    @abstractmethod
    def set_volume(self, ctx: commands.Context, value: float) -> None:
        pass

    @abstractmethod
    def skip_flag(self, ctx: commands.Context) -> bool:
        pass

    @abstractmethod
    def set_skip_flag(self, ctx: commands.Context, value: bool) -> None:
        pass

    @abstractmethod
    def shuffle_queue(self, ctx: commands.Context) -> None:
        pass

    @abstractmethod
    def set_queue(self, ctx: commands.Context, value: list[MusicData]) -> None:
        pass

    @abstractmethod
    def remove_from_queue(self, ctx: commands.Context, index: int) -> None:
        pass


class InternalGuildsData(GuildsData):
    def __init__(self) -> None:
        self._queue: dict[int, list[MusicData]] = {}
        self._chat: dict[int, AIChat] = {}
        self._is_looping: dict[int, bool] = {}
        self._volume: dict[int, float] = {}
        self._skip_flag: dict[int, bool] = {}

    def chat(self, ctx: commands.Context) -> AIChat:
        id = guild_id(ctx, accepts_dm=True)
        return self._chat.setdefault(id, AIChat())

    def queue(self, ctx: commands.Context) -> list[MusicData]:
        guild_id = guild(ctx).id
        return self._queue.setdefault(guild_id, [])

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

    def shuffle_queue(self, ctx: commands.Context) -> None:
        guild_id = guild(ctx).id
        queue = self._queue[guild_id]
        if len(queue) > 1:
            first = queue.pop(0)
            random.shuffle(queue)
            queue.insert(0, first)
            self._queue[guild_id] = queue

    def remove_from_queue(self, ctx: commands.Context, index: int) -> None:
        guild_id = guild(ctx).id
        queue = self._queue[guild_id]
        queue.pop(index)
        self._queue[guild_id] = queue

    def set_queue(self, ctx: commands.Context, value: list[MusicData]):
        guild_id = guild(ctx).id
        self._queue[guild_id] = value


class ExternalGuildsData(GuildsData):
    def __init__(self) -> None:
        self.internal: GuildsData = InternalGuildsData()

    def chat(self, ctx: commands.Context) -> AIChat:
        return self.internal.chat(ctx)

    def queue(self, ctx: commands.Context) -> list[MusicData]:
        return self.internal.queue(ctx)

    def is_looping(self, ctx: commands.Context) -> bool:
        return self.internal.is_looping(ctx)

    def set_looping(self, ctx: commands.Context, value: bool):
        self.internal.set_looping(ctx, value)

    def volume(self, ctx: commands.Context) -> float:
        return self.internal.volume(ctx)

    def set_volume(self, ctx: commands.Context, value: float):
        self.internal.set_volume(ctx, value)

    def skip_flag(self, ctx: commands.Context) -> bool:
        return self.internal.skip_flag(ctx)

    def set_skip_flag(self, ctx: commands.Context, value: bool):
        self.internal.set_skip_flag(ctx, value)

    def shuffle_queue(self, ctx: commands.Context) -> None:
        self.internal.shuffle_queue(ctx)

    def remove_from_queue(self, ctx: commands.Context, index: int) -> None:
        self.internal.remove_from_queue(ctx, index)

    def set_queue(self, ctx: commands.Context, value: list[MusicData]):
        self.internal.set_queue(ctx, value)


global guild_data
guild_data: GuildsData = ExternalGuildsData()

global guild_ids
guild_ids: dict[int, str] = dict()
