from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from src.config import Settings


@dataclass(frozen=True)
class Vault:
    root: Path | None = None

    @property
    def available(self) -> bool:
        return self.root is not None


def from_settings(settings: Settings) -> Vault:
    configured = settings.vault_path
    if not configured:
        return Vault()
    root = Path(configured)
    return Vault(root=root) if root.is_dir() else Vault()


_configured = Vault()


def configure(vault: Vault) -> None:
    global _configured
    _configured = vault


def configured() -> Vault:
    return _configured
