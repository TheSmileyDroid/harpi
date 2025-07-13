"""Base cog class with usage tracking capabilities."""

from __future__ import annotations

import logging
from typing import Optional

from discord.ext import commands

from src.services.cog_manager import cog_manager


class TrackedCog(commands.Cog):
    """Base cog class that automatically tracks command usage."""

    def __init__(self) -> None:
        """Initialize the tracked cog."""
        super().__init__()
        self.logger = logging.getLogger(self.__class__.__name__)

    def track_command_usage(self, command_name: str, user_id: Optional[str] = None) -> None:
        """Track usage of a command.
        
        Args:
            command_name: Name of the command that was used
            user_id: ID of the user who used the command
        """
        try:
            cog_name = self.__class__.__name__
            cog_manager.record_command_usage(cog_name, command_name, user_id)
        except Exception as e:
            self.logger.error(f"Failed to track command usage: {e}")

    async def cog_after_invoke(self, ctx: commands.Context) -> None:
        """Called after every command in this cog is invoked."""
        if ctx.command:
            user_id = str(ctx.author.id) if ctx.author else None
            self.track_command_usage(ctx.command.name, user_id)