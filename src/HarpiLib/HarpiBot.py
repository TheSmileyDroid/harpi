from discord.ext import commands
from src.HarpiLib.api import HarpiAPI


class HarpiBot(commands.Bot):
    """Harpi bot."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.api: HarpiAPI = HarpiAPI(self)
