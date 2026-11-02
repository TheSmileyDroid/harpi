"""The panel speaks Brazilian Portuguese (AGENTS.md).

A word from the English interface vocabulary in a string a person can read
fails this test. The scan covers template text nodes, the attributes that
name a control, a field or an image, and the string literals in scripts,
in template expressions and in ``.ts`` modules.

A bare lowercase identifier that happens to match an English word -- a
state value such as ``"connected"``, a browser event such as ``"online"``
-- is code, not copy, and is listed in ``CODE_VALUES``. Copy in the
interface is never lowercase, so an upper- or mixed-case literal is always
scanned.
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
    "link",
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

CODE_VALUES: frozenset[str] = frozenset({
    "active",
    "archived",
    "close",
    "closed",
    "conflict",
    "connect",
    "connected",
    "connecting",
    "discord",
    "disconnect",
    "empty",
    "end",
    "error",
    "failed",
    "idle",
    "image",
    "link",
    "loading",
    "missing",
    "narrator",
    "off",
    "offline",
    "online",
    "open",
    "panel",
    "pass",
    "pending",
    "player",
    "queue",
    "ready",
    "reconnecting",
    "remove",
    "scene",
    "search",
    "select",
    "sheet",
    "spectator",
    "table",
    "token",
    "track",
    "unavailable",
    "INPUT",
    "TEXTAREA",
    "SELECT",
})

WORD = re.compile(r"[A-Za-z]+")
STYLE = re.compile(r"<style\b[^>]*>[\s\S]*?</style>")
SCRIPT = re.compile(r"<script\b[^>]*>([\s\S]*?)</script>")
TEXT_NODE = re.compile(r">([^<>]+)<")
ATTRIBUTE_VALUE = re.compile(
    r'(?:aria-label|placeholder|title|alt|label|message)\s*=\s*"([^"]*)"',
)
STRING_LITERAL = re.compile(r'"([^"\\\n]*)"|\'([^\'\\\n]*)\'')
SCANNED = ("*.svelte", "*.html")


def _english(text: str) -> list[str]:
    return [
        word for word in WORD.findall(text) if word.lower() in ENGLISH_WORDS
    ]


def _blank(match: re.Match[str]) -> str:
    return re.sub(r"[^\n]", " ", match.group(0))


def _without_expressions(source: str) -> str:
    kept: list[str] = []
    depth = 0
    for character in source:
        if character == "{":
            depth += 1
            kept.append(" ")
        elif character == "}":
            depth = max(0, depth - 1)
            kept.append(" ")
        elif depth:
            kept.append("\n" if character == "\n" else " ")
        else:
            kept.append(character)
    return "".join(kept)


def _expression_spans(source: str) -> list[tuple[int, int]]:
    spans: list[tuple[int, int]] = []
    depth = 0
    start = 0
    for index, character in enumerate(source):
        if character == "{":
            if depth == 0:
                start = index + 1
            depth += 1
        elif character == "}" and depth:
            depth -= 1
            if depth == 0:
                spans.append((start, index))
    return spans


def _line(source: str, position: int) -> int:
    return source.count("\n", 0, position) + 1


def _literal(match: re.Match[str]) -> str:
    return match.group(1) or match.group(2) or ""


def _is_copy(literal: str) -> bool:
    if " " in literal:
        return True
    return literal.isalpha() and literal not in CODE_VALUES


def _literals(source: str, offset: int = 0) -> list[tuple[int, str]]:
    return [
        (offset + match.start(), _literal(match))
        for match in STRING_LITERAL.finditer(source)
        if _is_copy(_literal(match))
    ]


def _copies(path: Path) -> list[tuple[int, str]]:
    source = path.read_text()
    masked = STYLE.sub(_blank, source)
    template = SCRIPT.sub(_blank, masked)
    plain = _without_expressions(template)
    found: list[tuple[int, str]] = [
        (match.start(), match.group(1)) for match in TEXT_NODE.finditer(plain)
    ]
    found.extend(
        (match.start(), match.group(1))
        for match in ATTRIBUTE_VALUE.finditer(template)
    )
    for start, end in _expression_spans(template):
        found.extend(_literals(source[start:end], start))
    for match in SCRIPT.finditer(masked):
        found.extend(
            _literals(source[match.start(1) : match.end(1)], match.start(1))
        )
    if path.suffix == ".ts":
        found.extend(_literals(source))
    return [(_line(source, position), text) for position, text in found]


def _scanned_files() -> list[Path]:
    files = [
        path for pattern in SCANNED for path in sorted(WEB_SRC.rglob(pattern))
    ]
    files.extend(
        path
        for path in sorted(WEB_SRC.rglob("*.ts"))
        if not path.name.endswith(".test.ts") and "contract" not in path.parts
    )
    return files


def _failures(path: Path) -> list[str]:
    return [
        f"{path.relative_to(REPO)}:{number}: {', '.join(words)} — {text.strip()}"
        for number, text in _copies(path)
        if (words := _english(text))
    ]


def test_the_panel_has_no_english_interface_text() -> None:
    failures = [
        failure for path in _scanned_files() for failure in _failures(path)
    ]
    assert not failures, "\n".join(failures)
