"""Modelo para o canvas."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class CanvasData(BaseModel):
    """Dados do canvas para uma guilda."""

    elements: List[Dict[str, Any]] = Field(default_factory=list)
    app_state: Optional[Dict[str, Any]] = None


class CanvasStorage:
    """Armazenamento em memória para os dados do canvas."""

    _instance = None
    _storage: Dict[str, CanvasData] = {}

    def __new__(cls) -> CanvasStorage:
        """Singleton pattern implementation."""
        if cls._instance is None:
            cls._instance = super(CanvasStorage, cls).__new__(cls)
        return cls._instance

    def get_canvas(self, guild_id: str) -> CanvasData:
        """Retorna os dados do canvas para uma guilda específica.

        Args:
            guild_id (str): ID da guilda.

        Returns:
            CanvasData: Dados do canvas para a guilda.
        """
        if guild_id not in self._storage:
            self._storage[guild_id] = CanvasData()
        return self._storage[guild_id]

    def update_canvas(self, guild_id: str, canvas_data: CanvasData) -> None:
        """Atualiza os dados do canvas para uma guilda específica.

        Args:
            guild_id (str): ID da guilda.
            canvas_data (CanvasData): Novos dados do canvas.
        """
        self._storage[guild_id] = canvas_data
