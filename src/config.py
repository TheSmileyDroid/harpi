"""Settings: single home for every environment read.

DOC: https://docs.python.org/3/library/dataclasses.html
"""

from __future__ import annotations

import os
import re
from dataclasses import dataclass


def _port_from_env() -> int:
    try:
        return int(os.getenv("PORT", "8000"))
    except ValueError as e:
        raise ValueError("PORT must be an integer") from e


def _int_from_env(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, str(default)))
    except ValueError as e:
        raise ValueError(f"{name} must be an integer") from e


def _env_flag(name: str) -> bool:
    return os.getenv(name, "").lower() in ("1", "true", "yes")


def _env_or(name: str, default: str) -> str:
    return os.getenv(name) or default


def _env_or_none(name: str) -> str | None:
    return os.getenv(name) or None


def _allowlist_from_env() -> frozenset[int]:
    raw = os.getenv("PANEL_GUILD_ALLOWLIST", "")
    entries = [entry for entry in re.split(r"[,\s]+", raw.strip()) if entry]
    if not entries or any(not entry.isdigit() for entry in entries):
        return frozenset()
    return frozenset(int(entry) for entry in entries)


def _trusted_hosts_from_env() -> tuple[str, ...]:
    raw = os.getenv("PANEL_TRUSTED_HOSTS")
    if raw is None:
        return DEFAULT_TRUSTED_HOSTS
    hosts = tuple(host.strip() for host in raw.split(",") if host.strip())
    return hosts or DEFAULT_TRUSTED_HOSTS


DEFAULT_REDIRECT_URI = "http://localhost:8000/api/auth/discord/callback"
DEFAULT_TRUSTED_HOSTS = ("harpi.smileydroid.com.br", "localhost", "127.0.0.1")
DEFAULT_RETENTION_DAYS = 30


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
    db_path: str = "data/harpi.db"
    guild_allowlist: frozenset[int] = frozenset()
    public_mode: bool = False
    insecure_cookies: bool = False
    trusted_hosts: tuple[str, ...] = DEFAULT_TRUSTED_HOSTS
    work_dir: str = "data/work"
    vault_path: str | None = None
    log_path: str = "data/logs/harpi.log"
    log_level: str = "INFO"
    retention_days: int = DEFAULT_RETENTION_DAYS
    alert_webhook: str | None = None

    @classmethod
    def from_env(cls) -> Settings:
        return cls(
            discord_token=os.getenv("DISCORD_TOKEN"),
            prefix=_env_or("PREFIX", "-"),
            host=os.getenv("HOST", "127.0.0.1"),
            port=_port_from_env(),
            reload=_env_flag("RELOAD"),
            secret_key=os.environ.get("SECRET_KEY"),
            discord_client_id=os.getenv("DISCORD_CLIENT_ID"),
            discord_redirect_uri=_env_or(
                "DISCORD_REDIRECT_URI", DEFAULT_REDIRECT_URI
            ),
            ytdl_debug=_env_flag("HARPI_YTDL_DEBUG"),
            js_runtime_dirs=_env_or("HARPI_JS_RUNTIME_DIRS", ""),
            db_path=_env_or("HARPI_DB_PATH", "data/harpi.db"),
            guild_allowlist=_allowlist_from_env(),
            public_mode=_env_flag("PANEL_PUBLIC_MODE"),
            insecure_cookies=_env_flag("PANEL_INSECURE_COOKIES"),
            trusted_hosts=_trusted_hosts_from_env(),
            work_dir=_env_or("HARPI_WORK_DIR", "data/work"),
            vault_path=_env_or_none("HARPI_VAULT_PATH"),
            log_path=_env_or("HARPI_LOG_PATH", "data/logs/harpi.log"),
            log_level=_env_or("HARPI_LOG_LEVEL", "INFO").upper(),
            retention_days=_int_from_env(
                "PANEL_RETENTION_DAYS", DEFAULT_RETENTION_DAYS
            ),
            alert_webhook=os.getenv("PANEL_ALERT_WEBHOOK"),
        )
