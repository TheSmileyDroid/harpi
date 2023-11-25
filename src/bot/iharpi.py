from abc import ABC, abstractmethod
from discord.ext import commands


class IHarpi(ABC, commands.Bot):
    @abstractmethod
    async def setup_hook(self) -> None:
        pass

    @abstractmethod
    async def on_ready(self):
        pass

    @abstractmethod
    async def log_guilds(self):
        pass

    @abstractmethod
    async def on_command_error(self, ctx: commands.Context, error: Exception):
        pass
