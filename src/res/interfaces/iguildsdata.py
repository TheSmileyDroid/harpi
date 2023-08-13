from abc import ABCMeta, abstractmethod
from discord.ext import commands

from ..utils.aichat import AIChat
from .imusicqueue import IMusicQueue


class IGuildsData(metaclass=ABCMeta):
    @abstractmethod
    def chat(self, ctx: commands.Context) -> AIChat:
        pass

    @abstractmethod
    def queue(self, ctx: commands.Context) -> IMusicQueue:
        pass

    @abstractmethod
    def set_queue(self, ctx: commands.Context, value: IMusicQueue) -> None:
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
