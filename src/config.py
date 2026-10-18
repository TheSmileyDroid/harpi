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


DEFAULT_REDIRECT_URI = "http://localhost:8000/api/auth/discord/callback"


@dataclass(frozen=True, slots=True)
class Settings:
    discord_token: str | None
    prefix: str
    host: str
    port: int
    reload: bool
    secret_key: str | None
    discord_client_id: str | None = None
    discord_redirect_uri: str = DEFAULT_REDIRECT_URI
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
            discord_client_id=os.getenv("DISCORD_CLIENT_ID"),
            discord_redirect_uri=(
                os.getenv("DISCORD_REDIRECT_URI") or DEFAULT_REDIRECT_URI
            ),
            ytdl_debug=_env_flag("HARPI_YTDL_DEBUG"),
            js_runtime_dirs=os.getenv("HARPI_JS_RUNTIME_DIRS") or "",
        )
