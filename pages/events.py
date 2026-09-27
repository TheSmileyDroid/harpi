from __future__ import annotations

import asyncio
import json
from collections.abc import AsyncGenerator, Iterable
from pathlib import Path

from quart import Blueprint, Response

bp = Blueprint("events", __name__)

SHELL_ASSETS: tuple[Path, ...] = (
    Path("templates"),
    Path("static/css/app.css"),
    Path("web/src/app.html"),
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


def _reload_frame() -> str:
    return f"event: reload\ndata: {json.dumps({'scope': 'shell'})}\n\n"


async def _shell_changes() -> AsyncGenerator[str, None]:
    previous = _snapshot()
    yield ": connected\n\n"
    while True:
        await asyncio.sleep(POLL_SECONDS)
        current = _snapshot()
        if current != previous:
            previous = current
            yield _reload_frame()


@bp.get("/api/events")
def events():
    return Response(_shell_changes(), mimetype="text/event-stream")
