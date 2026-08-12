from typing import Any

from discord.ext import commands

from src.harpi_lib.audio.session_manager import SessionManager


class HarpiBot(commands.Bot):
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.sessions: SessionManager = SessionManager(self)
