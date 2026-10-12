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
    panel_token: str | None = None
    ytdl_debug: bool = False
    js_runtime_dirs: str = ""

    @classmethod
    def from_env(cls) -> Settings:
        return cls(
            discord_token=os.getenv("DISCORD_TOKEN"),
            prefix=os.getenv("PREFIX") or "-",
            host=os.getenv("HOST", "127.0.0.1"),
            port=_port_from_env(),
            reload=_env_flag("RELOAD"),
            secret_key=os.environ.get("SECRET_KEY"),
            panel_token=os.getenv("PANEL_TOKEN"),
            ytdl_debug=_env_flag("HARPI_YTDL_DEBUG"),
            js_runtime_dirs=os.getenv("HARPI_JS_RUNTIME_DIRS") or "",
        )
