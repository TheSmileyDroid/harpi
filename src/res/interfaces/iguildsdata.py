from abc import ABC, abstractmethod
from discord.ext import commands

from .imusicqueue import IMusicQueue


class IGuildsData(ABC):
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

    @abstractmethod
    def add_custom_data(self, ctx: commands.Context, key: str, value: str) -> None:
        pass

    @abstractmethod
    def get_custom_data(self, ctx: commands.Context, key: str) -> str:
        pass
