from __future__ import annotations

from src.storage.database import Database
from src.storage.registry import Registry

_registry: Registry | None = None
_database: Database | None = None


def init_registry(registry: Registry) -> None:
    global _registry
    _registry = registry


def get_registry() -> Registry | None:
    return _registry


def clear_registry() -> None:
    global _registry
    _registry = None


def init_database(database: Database) -> None:
    global _database
    _database = database


def get_database() -> Database | None:
    return _database


def clear_database() -> None:
    global _database
    _database = None
