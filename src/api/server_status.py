"""Shared server status computation for dashboard and HTMX polling."""

from __future__ import annotations

import time
from typing import TYPE_CHECKING

import psutil
from loguru import logger

from src.api.deps import run_on_bot_loop

if TYPE_CHECKING:
    from src.harpi_lib.harpi_bot import HarpiBot


async def get_server_status(guilds: list, *, bot: "HarpiBot") -> dict:
    """Compute current server status from system metrics and guild data.

    The music/queue counters read each guild's session status snapshot
    (sampled on the bot's event loop), so the dashboard and the HTMX
    fragment both consume the same read-model as the rest of the panel.
    """
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
            session = bot.sessions.get(int(g.id))
            if session is None:
                continue
            status = await run_on_bot_loop(session.sample_status())
            if status.queue:
                music_guilds += 1
                queue_total += len(status.queue)
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

    result["bot_latency"] = bot.latency * 1000 if bot.latency else 0
    result["bot_connected"] = bot.is_ready()

    return result
