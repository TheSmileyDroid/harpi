from __future__ import annotations

from src.storage.registry import Registry

_registry: Registry | None = None


def init_registry(registry: Registry) -> None:
    global _registry
    _registry = registry


def get_registry() -> Registry | None:
    return _registry


def clear_registry() -> None:
    global _registry
    _registry = None
