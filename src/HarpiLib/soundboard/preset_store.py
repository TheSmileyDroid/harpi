"""JSON file-based storage for soundboard presets."""

from __future__ import annotations

import json
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from loguru import logger

DATA_DIR = Path(__file__).parent.parent.parent.parent / "data" / "soundboard"


@dataclass
class SoundboardPreset:
    """A saved soundboard configuration."""

    id: str
    name: str
    guild_id: int
    nodes: list[dict[str, Any]]
    edges: list[dict[str, Any]]
    created_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    updated_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> SoundboardPreset:
        return cls(
            id=data["id"],
            name=data["name"],
            guild_id=data["guild_id"],
            nodes=data["nodes"],
            edges=data["edges"],
            created_at=data.get(
                "created_at", datetime.now(timezone.utc).isoformat()
            ),
            updated_at=data.get(
                "updated_at", datetime.now(timezone.utc).isoformat()
            ),
        )


class PresetStore:
    """Manages soundboard presets stored as JSON files per guild."""

    def __init__(self, data_dir: Path | None = None):
        self.data_dir = data_dir or DATA_DIR
        self.data_dir.mkdir(parents=True, exist_ok=True)

    def _get_guild_file(self, guild_id: int) -> Path:
        guild_dir = self.data_dir / str(guild_id)
        guild_dir.mkdir(parents=True, exist_ok=True)
        return guild_dir / "presets.json"

    def _load_guild_presets(
        self, guild_id: int
    ) -> dict[str, SoundboardPreset]:
        file_path = self._get_guild_file(guild_id)
        if not file_path.exists():
            return {}
        try:
            with open(file_path) as f:
                data = json.load(f)
            return {k: SoundboardPreset.from_dict(v) for k, v in data.items()}
        except (json.JSONDecodeError, KeyError) as e:
            logger.error(f"Failed to load presets for guild {guild_id}: {e}")
            return {}

    def _save_guild_presets(
        self, guild_id: int, presets: dict[str, SoundboardPreset]
    ) -> None:
        file_path = self._get_guild_file(guild_id)
        data = {k: v.to_dict() for k, v in presets.items()}
        with open(file_path, "w") as f:
            json.dump(data, f, indent=2)

    def list_presets(self, guild_id: int) -> list[SoundboardPreset]:
        """List all presets for a guild."""
        presets = self._load_guild_presets(guild_id)
        return list(presets.values())

    def get_preset(
        self, preset_id: str, guild_id: int
    ) -> SoundboardPreset | None:
        """Get a specific preset by ID."""
        presets = self._load_guild_presets(guild_id)
        return presets.get(preset_id)

    def create_preset(
        self,
        guild_id: int,
        name: str,
        nodes: list[dict[str, Any]],
        edges: list[dict[str, Any]],
    ) -> SoundboardPreset:
        """Create a new preset."""
        preset = SoundboardPreset(
            id=str(uuid.uuid4()),
            name=name,
            guild_id=guild_id,
            nodes=nodes,
            edges=edges,
        )
        presets = self._load_guild_presets(guild_id)
        presets[preset.id] = preset
        self._save_guild_presets(guild_id, presets)
        logger.info(
            f"Created preset '{name}' ({preset.id}) for guild {guild_id}"
        )
        return preset

    def update_preset(
        self,
        preset_id: str,
        guild_id: int,
        name: str | None = None,
        nodes: list[dict[str, Any]] | None = None,
        edges: list[dict[str, Any]] | None = None,
    ) -> SoundboardPreset | None:
        """Update an existing preset."""
        presets = self._load_guild_presets(guild_id)
        preset = presets.get(preset_id)
        if not preset:
            return None

        if name is not None:
            preset.name = name
        if nodes is not None:
            preset.nodes = nodes
        if edges is not None:
            preset.edges = edges
        preset.updated_at = datetime.now(timezone.utc).isoformat()

        presets[preset_id] = preset
        self._save_guild_presets(guild_id, presets)
        logger.info(f"Updated preset {preset_id} for guild {guild_id}")
        return preset

    def delete_preset(self, preset_id: str, guild_id: int) -> bool:
        """Delete a preset."""
        presets = self._load_guild_presets(guild_id)
        if preset_id not in presets:
            return False

        del presets[preset_id]
        self._save_guild_presets(guild_id, presets)
        logger.info(f"Deleted preset {preset_id} for guild {guild_id}")
        return True
