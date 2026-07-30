"""Shared server status computation for dashboard and HTMX polling."""

from __future__ import annotations

import time
from typing import TYPE_CHECKING

import psutil
from loguru import logger

from src.api.deps import get_api

if TYPE_CHECKING:
    from src.harpi_lib.harpi_bot import HarpiBot


def get_server_status(guilds: list, *, bot: HarpiBot | None = None) -> dict:
    """Compute current server status from system metrics and guild data."""
    cpu_percent = psutil.cpu_percent()
    mem = psutil.virtual_memory()

    uptime_seconds = int(time.time() - psutil.boot_time())
    uptime_hours = uptime_seconds // 3600
    uptime_minutes = (uptime_seconds % 3600) // 60
    uptime_formatted = f"{uptime_hours}h {uptime_minutes}m"

    music_guilds = 0
    queue_total = 0
    for g in guilds:
        try:
            gc = get_api().get_guild_config(int(g.id))
            if gc and gc.queue:
                music_guilds += 1
                queue_total += len(gc.queue)
        except Exception as e:
            logger.debug(f"Skipping guild {g.id} status: {e}")

    result = {
        "cpu_percent": cpu_percent,
        "memory_percent": mem.percent,
        "memory_total": mem.total,
        "memory_used": mem.used,
        "uptime_formatted": uptime_formatted,
        "music_guilds": music_guilds,
        "queue_total": queue_total,
    }

    if bot is not None:
        result["bot_latency"] = bot.latency * 1000 if bot.latency else 0
        result["bot_connected"] = bot.is_ready()

    return result
