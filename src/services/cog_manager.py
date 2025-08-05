"""Service for managing cog configuration and usage tracking."""

from __future__ import annotations

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

import discord.ext.commands as commands

from src.models.cog import (
    CogConfiguration,
    CogInfo,
    CommandInfo,
    CommandUsage,
)


class CogManagerService:
    """Service for managing Discord cogs configuration and usage."""

    def __init__(self, config_file: str = "cog_config.json") -> None:
        """Initialize the cog manager service.

        Args:
            config_file: Path to the configuration file.
        """
        self.config_file = Path(config_file)
        self.logger = logging.getLogger(__name__)
        self._config: Optional[CogConfiguration] = None

    @property
    def config(self) -> CogConfiguration:
        """Get the current configuration, loading it if necessary."""
        if self._config is None:
            self._config = self.load_config()
        return self._config

    def load_config(self) -> CogConfiguration:
        """Load configuration from file or create default."""
        try:
            if self.config_file.exists():
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    
                # Parse datetime strings back to datetime objects
                if 'last_updated' in data and isinstance(data['last_updated'], str):
                    try:
                        data['last_updated'] = datetime.fromisoformat(data['last_updated'])
                    except ValueError:
                        data['last_updated'] = datetime.now()
                        
                # Parse datetime strings in usage stats
                for cog_name, cog_data in data.get('cogs', {}).items():
                    for usage in cog_data.get('usage_stats', []):
                        if 'last_used' in usage and isinstance(usage['last_used'], str):
                            try:
                                usage['last_used'] = datetime.fromisoformat(usage['last_used'])
                            except ValueError:
                                usage['last_used'] = None
                                
                return CogConfiguration(**data)
            else:
                self.logger.info("Config file not found, creating default configuration")
                return self._create_default_config()
        except Exception as e:
            self.logger.error(f"Error loading config: {e}")
            return self._create_default_config()

    def save_config(self) -> None:
        """Save current configuration to file."""
        try:
            self.config.last_updated = datetime.now()
            # Convert to JSON-serializable format
            config_dict = self.config.model_dump(mode='json')
            
            # Convert datetime objects to ISO strings
            def serialize_datetime(obj):
                if isinstance(obj, datetime):
                    return obj.isoformat()
                raise TypeError(f"Object of type {type(obj)} is not JSON serializable")
            
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(
                    config_dict,
                    f,
                    indent=2,
                    default=serialize_datetime,
                    ensure_ascii=False
                )
            self.logger.info("Configuration saved successfully")
        except Exception as e:
            self.logger.error(f"Error saving config: {e}")

    def _create_default_config(self) -> CogConfiguration:
        """Create default configuration with all known cogs."""
        config = CogConfiguration()
        
        # Default cogs that are known to exist
        default_cogs = {
            "BasicCog": CogInfo(
                name="BasicCog",
                description="Basic bot commands like ping, echo, and system status",
                enabled=True
            ),
            "DiceCog": CogInfo(
                name="DiceCog", 
                description="RPG dice rolling commands",
                enabled=True
            ),
            "MusicCog": CogInfo(
                name="MusicCog",
                description="Music player commands for voice channels",
                enabled=True
            ),
            "TTSCog": CogInfo(
                name="TTSCog",
                description="Text-to-speech commands",
                enabled=True
            ),
            "AiCog": CogInfo(
                name="AiCog",
                description="AI-powered chat and assistant commands",
                enabled=True
            )
        }
        
        config.cogs = default_cogs
        self.save_config()
        return config

    def get_all_cogs(self) -> Dict[str, CogInfo]:
        """Get all cog configurations."""
        return self.config.cogs

    def get_cog(self, cog_name: str) -> Optional[CogInfo]:
        """Get configuration for a specific cog."""
        return self.config.cogs.get(cog_name)

    def is_cog_enabled(self, cog_name: str) -> bool:
        """Check if a cog is enabled."""
        cog = self.get_cog(cog_name)
        return cog.enabled if cog else False

    def toggle_cog(self, cog_name: str, enabled: bool) -> bool:
        """Enable or disable a cog.
        
        Args:
            cog_name: Name of the cog to toggle
            enabled: Whether to enable or disable
            
        Returns:
            True if operation was successful, False otherwise
        """
        try:
            if cog_name not in self.config.cogs:
                self.logger.warning(f"Cog {cog_name} not found in configuration")
                return False
                
            self.config.cogs[cog_name].enabled = enabled
            self.save_config()
            self.logger.info(f"Cog {cog_name} {'enabled' if enabled else 'disabled'}")
            return True
        except Exception as e:
            self.logger.error(f"Error toggling cog {cog_name}: {e}")
            return False

    def update_cog_info(self, cog_name: str, cog: commands.Cog) -> None:
        """Update cog information from the actual Discord cog instance."""
        try:
            if cog_name not in self.config.cogs:
                self.config.cogs[cog_name] = CogInfo(name=cog_name, enabled=True)

            cog_info = self.config.cogs[cog_name]
            
            # Update description from cog docstring
            if hasattr(cog, '__doc__') and cog.__doc__:
                cog_info.description = cog.__doc__.strip()

            # Update commands information
            commands_info = []
            for command in cog.get_commands():
                cmd_info = CommandInfo(
                    name=command.name,
                    description=command.help or command.brief or "No description available",
                    aliases=list(command.aliases) if command.aliases else [],
                    usage=f"-{command.name} {command.signature}" if command.signature else f"-{command.name}"
                )
                commands_info.append(cmd_info)

            cog_info.commands = commands_info
            self.save_config()
            
        except Exception as e:
            self.logger.error(f"Error updating cog info for {cog_name}: {e}")

    def record_command_usage(self, cog_name: str, command_name: str, user_id: Optional[str] = None) -> None:
        """Record usage of a command."""
        try:
            if cog_name not in self.config.cogs:
                return

            cog_info = self.config.cogs[cog_name]
            
            # Find existing usage record or create new one
            usage_record = None
            for usage in cog_info.usage_stats:
                if usage.command_name == command_name:
                    usage_record = usage
                    break
                    
            if usage_record is None:
                usage_record = CommandUsage(command_name=command_name)
                cog_info.usage_stats.append(usage_record)

            # Update usage statistics
            usage_record.total_uses += 1
            usage_record.last_used = datetime.now()
            if user_id:
                usage_record.last_user = user_id

            self.save_config()
            
        except Exception as e:
            self.logger.error(f"Error recording command usage for {cog_name}.{command_name}: {e}")

    def get_command_usage(self, cog_name: str, command_name: Optional[str] = None) -> List[CommandUsage]:
        """Get usage statistics for commands in a cog."""
        cog = self.get_cog(cog_name)
        if not cog:
            return []
            
        if command_name:
            return [usage for usage in cog.usage_stats if usage.command_name == command_name]
        return cog.usage_stats


# Global instance
cog_manager = CogManagerService()