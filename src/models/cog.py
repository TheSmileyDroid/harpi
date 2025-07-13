"""Models for cog management and usage tracking."""

from __future__ import annotations

from datetime import datetime
from typing import Dict, List, Optional

from pydantic import BaseModel, Field


class CommandInfo(BaseModel):
    """Information about a Discord command."""

    name: str = Field(..., description="Command name")
    description: Optional[str] = Field(None, description="Command description")
    aliases: List[str] = Field(default_factory=list, description="Command aliases")
    usage: Optional[str] = Field(None, description="Command usage example")


class CommandUsage(BaseModel):
    """Usage statistics for a command."""

    command_name: str = Field(..., description="Command name")
    total_uses: int = Field(0, description="Total number of uses")
    last_used: Optional[datetime] = Field(None, description="Last time used")
    last_user: Optional[str] = Field(None, description="Last user who used it")


class CogInfo(BaseModel):
    """Information about a Discord cog."""

    name: str = Field(..., description="Cog name")
    description: Optional[str] = Field(None, description="Cog description")
    enabled: bool = Field(True, description="Whether the cog is enabled")
    commands: List[CommandInfo] = Field(default_factory=list, description="Commands in this cog")
    usage_stats: List[CommandUsage] = Field(default_factory=list, description="Usage statistics")


class CogConfiguration(BaseModel):
    """Configuration for all cogs."""

    cogs: Dict[str, CogInfo] = Field(default_factory=dict, description="Cog configurations")
    last_updated: datetime = Field(default_factory=datetime.now, description="Last configuration update")


class CogStatusUpdate(BaseModel):
    """Request model for updating cog status."""

    enabled: bool = Field(..., description="Whether to enable or disable the cog")


class CommandUsageUpdate(BaseModel):
    """Request model for updating command usage."""

    command_name: str = Field(..., description="Command name")
    user_id: Optional[str] = Field(None, description="User who used the command")