from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from src.config import Settings


@dataclass(frozen=True)
class Vault:
    root: Path | None = None

    @property
    def available(self) -> bool:
        return self.root is not None and self.root.is_dir()


def from_settings(settings: Settings) -> Vault:
    configured = settings.vault_path
    return Vault(root=Path(configured) if configured else None)


_configured = Vault()


def configure(vault: Vault) -> None:
    global _configured
    _configured = vault


def configured() -> Vault:
    return _configured
