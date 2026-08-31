"""Settings: single home for every environment read.

DOC: https://docs.python.org/3/library/dataclasses.html
"""

from __future__ import annotations

import os
from dataclasses import dataclass


def _port_from_env() -> int:
    try:
        return int(os.getenv("PORT", "8000"))
    except ValueError as e:
        raise ValueError("PORT must be an integer") from e


def _env_flag(name: str) -> bool:
    return os.getenv(name, "").lower() in ("1", "true", "yes")


@dataclass(frozen=True, slots=True)
class Settings:
    discord_token: str | None
    prefix: str
    host: str
    port: int
    reload: bool
    secret_key: str | None

    @classmethod
    def from_env(cls) -> Settings:
        return cls(
            discord_token=os.getenv("DISCORD_TOKEN"),
            prefix=os.getenv("PREFIX") or "-",
            host=os.getenv("HOST", "0.0.0.0"),
            port=_port_from_env(),
            reload=_env_flag("RELOAD"),
            secret_key=os.environ.get("SECRET_KEY"),
        )
