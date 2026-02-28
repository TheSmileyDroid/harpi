from typing import Any

from discord.ext import commands
from src.harpi_lib.api import HarpiAPI


class HarpiBot(commands.Bot):
    """Harpi bot."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.api: HarpiAPI = HarpiAPI(self)
