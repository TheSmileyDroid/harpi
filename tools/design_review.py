"""Design review capture: serve the panel offline, screenshot it, digest the UI.

Part of the design review (docs/adr/0001-cheap-vision-reviewer.md). This tool
serves the panel with faked bot state (the real bot never starts: the
``before_serving`` hook is stripped and a fake must be registered first, or
the tool exits), captures full-page and viewport-height screenshots of Home
and Music at 1280 and 375 widths, and prints the UI digest the verdict must
carry. The reviewer (agent or human) reads the shots and writes
``.scratch/design-review/verdict.json``; ``tools/design_review_gate.py``
fails until that verdict matches the digest.
"""

from __future__ import annotations

import asyncio
import hashlib
import os
import sys
import threading
import time
from pathlib import Path
from typing import Any, cast

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))
os.chdir(REPO)

OUT_DIR = REPO / ".scratch" / "design-review" / "shots"
VERDICT_PATH = REPO / ".scratch" / "design-review" / "verdict.json"
PORT = 8737

# The UI surfaces whose bytes the verdict covers. A change here makes every
# existing verdict stale and re-opens the review.
UI_DIRS = ("pages", "templates", "static/css")
# The rubric's sources: when these change, what "good" means changed and
# every verdict is stale. The capture tool itself is deliberately absent:
# it does not touch the UI or the judgment.
UI_FILES = (
    ".opencode/skills/design-review/SKILL.md",
    "docs/agents/design.md",
)

VIEWPORTS = (
    ("desktop", 1280, 800),
    ("mobile", 375, 720),
)
PAGES = (
    ("home", "/"),
    ("music", "/music?guild_id=1"),
)
GUILD_ID = 1
CHANNEL_ID = 42


def ui_digest() -> str:
    """A stable hash over every byte the design language governs."""
    h = hashlib.sha256()
    bases: list[Path] = [REPO / d for d in UI_DIRS] + [
        REPO / f for f in UI_FILES
    ]
    files: set[Path] = set()
    for base in bases:
        if base.is_file():
            files.add(base)
        else:
            files.update(
                p
                for p in base.rglob("*")
                if p.is_file() and "__pycache__" not in p.parts
            )
    for p in sorted(files):
        h.update(str(p.relative_to(REPO)).encode())
        h.update(p.read_bytes())
    return h.hexdigest()[:16]


def build_bot() -> Any:
    """The offline bot stack from the integration tests: real session
    machinery, faked Discord and yt-dlp seams. Import-time patches mirror
    tests/test_panel_session_integration.py so there is one fake stack."""

    import src.harpi_lib.audio.session as session_module
    from pages import music as guild_module
    from tests.conftest import FakeMusicDataFactory
    from tests.test_panel_session_integration import (
        PanelBot,
        PanelGuild,
        StageSourceFactory,
    )

    class ReviewBot(PanelBot):
        """Adds the home-page readiness surface."""

        def is_ready(self) -> bool:
            return True

        def is_closed(self) -> bool:
            return False

    # The integration tests patch these seams with monkeypatch; the capture
    # tool patches them for the process lifetime instead. ty is right that
    # the types differ — that is the seam working.
    session_module.YTMusicData = FakeMusicDataFactory  # ty: ignore[invalid-assignment]
    session_module.YoutubeDLSource = StageSourceFactory  # ty: ignore[invalid-assignment]
    guild_module.YTMusicData = FakeMusicDataFactory  # ty: ignore[invalid-assignment]

    bot: Any = ReviewBot(PanelGuild(GUILD_ID))
    return bot


async def _drive(base: str) -> None:
    """Connect and queue tracks through the panel's own HTTP surface so the
    shots show a live panel, not an empty one."""
    import httpx

    async with httpx.AsyncClient(base_url=base, follow_redirects=True) as c:
        await c.get(f"/music?guild_id={GUILD_ID}")
        r = await c.post(
            "/music",
            data={
                "action": "connect",
                "guild_id": GUILD_ID,
                "channel_id": CHANNEL_ID,
            },
            headers={"HX-Request": "true", "HX-Target": "selector"},
        )
        assert r.status_code == 200, r.status_code
        for term in ("warriors", "second"):
            r = await c.post(
                "/music",
                data={"action": "add", "value": term},
                headers={"HX-Request": "true", "HX-Target": "queue"},
            )
            assert r.status_code == 200, (term, r.status_code)


def capture(base: str) -> list[Path]:
    from playwright.sync_api import sync_playwright

    shots: list[Path] = []
    with sync_playwright() as p:
        browser = p.chromium.launch()
        for name, width, height in VIEWPORTS:
            page = browser.new_page(
                viewport={"width": width, "height": height}
            )
            for label, path in PAGES:
                page.goto(f"{base}{path}")
                page.wait_for_timeout(1200)  # htmx poll + tailwind settle
                full = OUT_DIR / f"{name}-{label}-full.png"
                page.screenshot(path=str(full), full_page=True)
                # A viewport-height shot: full-page captures paint fixed
                # bars at the scroll seam, so only this one shows where the
                # transport really sits.
                framed = OUT_DIR / f"{name}-{label}-viewport.png"
                page.screenshot(path=str(framed), full_page=False)
                shots += [full, framed]
            page.close()
        browser.close()
    return shots


def main() -> None:
    os.environ["SECRET_KEY"] = "design-review"
    os.environ.pop("DISCORD_TOKEN", None)

    from app import app as quart_app
    from src import bot_state as deps
    from src.harpi_lib.harpi_bot import HarpiBot

    # Fail closed: fakes first, real-bot spawn impossible second.
    quart_app.before_serving_funcs = []
    bot = build_bot()
    assert not isinstance(bot, HarpiBot), "fake bot required"
    deps.init_bot(cast(Any, bot))
    quart_app.secret_key = "design-review"

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    for old in OUT_DIR.glob("*.png"):
        old.unlink()

    import uvicorn

    config = uvicorn.Config(
        quart_app, host="127.0.0.1", port=PORT, log_level="warning"
    )
    server = uvicorn.Server(config)
    threading.Thread(target=server.run, daemon=True).start()
    for _ in range(50):
        time.sleep(0.2)
        if server.started:
            break
    assert server.started, "panel did not start"

    base = f"http://127.0.0.1:{PORT}"
    errors: list[Exception] = []

    def drive() -> None:
        try:
            asyncio.run(_drive(base))
        except Exception as exc:
            errors.append(exc)

    t = threading.Thread(target=drive)
    t.start()
    t.join()
    if errors:
        raise errors[0]

    shots = capture(base)
    server.should_exit = True

    digest = ui_digest()
    print("DIGEST:", digest)
    for s in shots:
        print("SHOT:", s.relative_to(REPO))
    print(f"Verdict goes to {VERDICT_PATH} with digest {digest}.")


if __name__ == "__main__":
    main()
