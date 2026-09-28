"""Playwright backend harness: the real Quart app over a fake bot.

Boots the production app with test credentials, a fake bot, and control
endpoints under /__test__ that let the browser test push live changes.
Only the bot handle is faked, so auth, routing, the SSE stream, and the
status serialization all run as they do in production.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from quart import request, session

import app as app_module
from src import bot_state
from src.harpi_lib.audio.session import SessionStatus
from src.harpi_lib.music.ytmusic import YTMusicData
from src.panel import state as panel_state
from tests.test_music_page import (
    GUILD_A,
    FakeBot,
    FakeGuild,
    FakeSession,
    playing_status,
)

quart_app = app_module.app


class HarnessBot(FakeBot):
    def __init__(self, guilds, session_obj):
        super().__init__(guilds, session_obj)
        self.online = True

    def is_ready(self) -> bool:
        return self.online

    def is_closed(self) -> bool:
        return not self.online


def status_for(title: str) -> SessionStatus:
    return playing_status(
        guild_id=GUILD_A,
        channel_id=42,
        current_music=YTMusicData(
            {
                "title": title,
                "url": f"https://example.com/{title}",
                "duration": 120,
            }
        ),
    )


session_obj = FakeSession(status_for("Now Track"))
bot = HarnessBot([FakeGuild(GUILD_A, "Alpha Guild")], session_obj)


async def _run_inline(coro, timeout: float | None = None):
    del timeout
    return await coro


panel_state.run_on_bot_loop = _run_inline
bot_state.init_bot(bot)
app_module.run_bot_in_background = lambda settings: None


@quart_app.after_request
async def select_guild(response):
    if session.get("authenticated") is True and session.get("guild_id") is None:
        session["guild_id"] = str(GUILD_A)
    return response


@quart_app.get("/__test__/ping")
async def ping():
    return {"ok": True}


@quart_app.post("/__test__/track")
async def set_track():
    payload = await request.get_json()
    session_obj._status = status_for(payload["title"])
    return {"ok": True}


@quart_app.post("/__test__/bot")
async def set_bot():
    payload = await request.get_json()
    bot.online = bool(payload["online"])
    return {"ok": True}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        quart_app,
        host="127.0.0.1",
        port=int(os.getenv("PORT", "8000")),
        log_level="warning",
    )
