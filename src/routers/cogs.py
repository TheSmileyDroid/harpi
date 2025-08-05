"""Router for cog management and configuration."""

from __future__ import annotations

from typing import Dict, List

from fastapi import APIRouter, HTTPException, Request

from src.models.cog import (
    CogInfo,
    CogStatusUpdate,
    CommandUsage,
    CommandUsageUpdate,
)
from src.services.cog_manager import cog_manager

router = APIRouter(
    responses={404: {"description": "Not found"}},
)


@router.get("/", response_model=Dict[str, CogInfo])
async def get_all_cogs() -> Dict[str, CogInfo]:
    """Get all available cogs with their configuration and status.

    Returns a dictionary mapping cog names to their configuration,
    including enabled status, commands, and usage statistics.

    Returns:
        Dict[str, CogInfo]: All cog configurations
    """
    return cog_manager.get_all_cogs()


@router.get("/{cog_name}", response_model=CogInfo)
async def get_cog(cog_name: str) -> CogInfo:
    """Get configuration for a specific cog.

    Args:
        cog_name: Name of the cog to retrieve

    Returns:
        CogInfo: The cog configuration

    Raises:
        HTTPException: If cog is not found
    """
    cog = cog_manager.get_cog(cog_name)
    if not cog:
        raise HTTPException(status_code=404, detail=f"Cog '{cog_name}' not found")
    return cog


@router.post("/{cog_name}/toggle")
async def toggle_cog(cog_name: str, status_update: CogStatusUpdate, request: Request) -> Dict[str, str]:
    """Enable or disable a cog.

    Args:
        cog_name: Name of the cog to toggle
        status_update: New status for the cog
        request: FastAPI request object to access bot instance

    Returns:
        Dict[str, str]: Status message

    Raises:
        HTTPException: If cog is not found or operation fails
    """
    # Check if cog exists
    if not cog_manager.get_cog(cog_name):
        raise HTTPException(status_code=404, detail=f"Cog '{cog_name}' not found")

    success = cog_manager.toggle_cog(cog_name, status_update.enabled)
    if not success:
        raise HTTPException(status_code=500, detail=f"Failed to toggle cog '{cog_name}'")

    # Note: In a real implementation, you might want to dynamically reload the bot
    # when cogs are toggled. For now, we'll just update the configuration.
    action = "enabled" if status_update.enabled else "disabled"
    return {
        "message": f"Cog '{cog_name}' has been {action}. Restart the bot to apply changes.",
        "status": action
    }


@router.get("/{cog_name}/commands")
async def get_cog_commands(cog_name: str) -> List[dict]:
    """Get all commands for a specific cog with their documentation.

    Args:
        cog_name: Name of the cog

    Returns:
        List[dict]: List of commands with their documentation

    Raises:
        HTTPException: If cog is not found
    """
    cog = cog_manager.get_cog(cog_name)
    if not cog:
        raise HTTPException(status_code=404, detail=f"Cog '{cog_name}' not found")

    commands = []
    for cmd in cog.commands:
        commands.append({
            "name": cmd.name,
            "description": cmd.description,
            "aliases": cmd.aliases,
            "usage": cmd.usage
        })

    return commands


@router.get("/{cog_name}/usage", response_model=List[CommandUsage])
async def get_cog_usage(cog_name: str) -> List[CommandUsage]:
    """Get usage statistics for all commands in a cog.

    Args:
        cog_name: Name of the cog

    Returns:
        List[CommandUsage]: Usage statistics for all commands

    Raises:
        HTTPException: If cog is not found
    """
    cog = cog_manager.get_cog(cog_name)
    if not cog:
        raise HTTPException(status_code=404, detail=f"Cog '{cog_name}' not found")

    return cog_manager.get_command_usage(cog_name)


@router.post("/{cog_name}/usage")
async def record_command_usage(
    cog_name: str, 
    usage_update: CommandUsageUpdate
) -> Dict[str, str]:
    """Record usage of a command (typically called by the bot).

    Args:
        cog_name: Name of the cog
        usage_update: Command usage information

    Returns:
        Dict[str, str]: Status message

    Raises:
        HTTPException: If cog is not found
    """
    cog = cog_manager.get_cog(cog_name)
    if not cog:
        raise HTTPException(status_code=404, detail=f"Cog '{cog_name}' not found")

    cog_manager.record_command_usage(
        cog_name, 
        usage_update.command_name, 
        usage_update.user_id
    )

    return {"message": f"Usage recorded for command '{usage_update.command_name}' in cog '{cog_name}'"}


@router.get("/{cog_name}/usage/{command_name}", response_model=List[CommandUsage])
async def get_command_usage(cog_name: str, command_name: str) -> List[CommandUsage]:
    """Get usage statistics for a specific command.

    Args:
        cog_name: Name of the cog
        command_name: Name of the command

    Returns:
        List[CommandUsage]: Usage statistics for the command

    Raises:
        HTTPException: If cog or command is not found
    """
    cog = cog_manager.get_cog(cog_name)
    if not cog:
        raise HTTPException(status_code=404, detail=f"Cog '{cog_name}' not found")

    usage_stats = cog_manager.get_command_usage(cog_name, command_name)
    if not usage_stats:
        raise HTTPException(status_code=404, detail=f"No usage data found for command '{command_name}'")

    return usage_stats