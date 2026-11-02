"""The panel speaks Brazilian Portuguese (AGENTS.md).

Every string a person reads in the Svelte app -- template text and the
attributes that name a control, a field or an image -- is scanned here. A
word from the English interface vocabulary means a translation was skipped.
"""

from __future__ import annotations

import re
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
WEB_SRC = REPO / "web" / "src"

ENGLISH_WORDS: frozenset[str] = frozenset({
    "access",
    "cancel",
    "carrier",
    "channel",
    "clear",
    "confirm",
    "connect",
    "connected",
    "connecting",
    "continue",
    "dismiss",
    "disconnect",
    "disconnected",
    "empty",
    "error",
    "failed",
    "failure",
    "guild",
    "hazard",
    "hide",
    "idle",
    "layer",
    "layers",
    "linked",
    "linking",
    "live",
    "load",
    "loading",
    "lost",
    "music",
    "next",
    "nothing",
    "offline",
    "online",
    "output",
    "pause",
    "paused",
    "play",
    "playing",
    "previous",
    "queue",
    "reconnect",
    "refresh",
    "remove",
    "removed",
    "results",
    "search",
    "select",
    "selected",
    "session",
    "show",
    "sign",
    "skip",
    "stale",
    "stopped",
    "track",
    "unavailable",
    "unknown",
    "voice",
    "waiting",
})

WORD = re.compile(r"[A-Za-z]+")
ATTRIBUTE_VALUE = re.compile(
    r'(?:aria-label|placeholder|title|alt|label|message)\s*=\s*"([^"]*)"',
)
TEXT_NODE = re.compile(r">([^<>]+)<")
EXPRESSION = re.compile(r"\{[^{}]*\}")
BLOCK = re.compile(r"<(script|style)\b[^>]*>[\s\S]*?</\1>")
SCANNED = ("*.svelte", "*.html")


def _english(text: str) -> list[str]:
    return [
        word for word in WORD.findall(text) if word.lower() in ENGLISH_WORDS
    ]


def _visible_strings(source: str) -> list[tuple[int, str]]:
    cleaned = EXPRESSION.sub(" ", BLOCK.sub(" ", source))
    found: list[tuple[int, str]] = []
    for number, line in enumerate(cleaned.splitlines(), start=1):
        matches = [*TEXT_NODE.finditer(line), *ATTRIBUTE_VALUE.finditer(line)]
        found.extend((number, match.group(1)) for match in matches)
    return found


def _failures(path: Path) -> list[str]:
    return [
        f"{path.relative_to(REPO)}:{number}: {', '.join(words)} — {text.strip()}"
        for number, text in _visible_strings(path.read_text())
        if (words := _english(text))
    ]


def test_the_panel_has_no_english_interface_text() -> None:
    failures = [
        failure
        for pattern in SCANNED
        for path in sorted(WEB_SRC.rglob(pattern))
        for failure in _failures(path)
    ]
    assert not failures, "\n".join(failures)
