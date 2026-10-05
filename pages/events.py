from __future__ import annotations

import asyncio
import json
from collections.abc import AsyncGenerator, Iterable
from pathlib import Path

from quart import Blueprint, Response

from pages.api import current_guild_id
from src.panel import state
from src.panel.schemas import StatusSnapshot

bp = Blueprint("events", __name__)

SHELL_ASSETS: tuple[Path, ...] = (
    Path("web/src/app.html"),
    Path("web/src/app.css"),
)

POLL_SECONDS = 0.5


def _snapshot(assets: Iterable[Path] = SHELL_ASSETS) -> dict[str, float]:
    snapshot: dict[str, float] = {}
    for asset in assets:
        if asset.is_dir():
            for file in asset.rglob("*"):
                if file.is_file():
                    snapshot[str(file)] = file.stat().st_mtime
        elif asset.is_file():
            snapshot[str(asset)] = asset.stat().st_mtime
    return snapshot


def _frame(event: str, data: dict | StatusSnapshot) -> str:
    payload = data.model_dump() if isinstance(data, StatusSnapshot) else data
    return f"event: {event}\ndata: {json.dumps(payload)}\n\n"


async def _stream(guild_id: int | None) -> AsyncGenerator[str, None]:
    previous_shell = _snapshot()
    previous_status = await state.status_snapshot(guild_id)
    yield ": connected\n\n"
    yield _frame("status", previous_status)
    while True:
        await asyncio.sleep(POLL_SECONDS)
        current_shell = _snapshot()
        if current_shell != previous_shell:
            previous_shell = current_shell
            yield _frame("reload", {"scope": "shell"})
        current_status = await state.status_snapshot(guild_id)
        if current_status != previous_status:
            previous_status = current_status
            yield _frame("status", current_status)


@bp.get("/api/events")
def events():
    return Response(_stream(current_guild_id()), mimetype="text/event-stream")
