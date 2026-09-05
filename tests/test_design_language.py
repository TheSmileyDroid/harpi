"""The design language rules a test can judge (docs/agents/design.md).

The vision reviewer only sees what pixels reveal; everything mechanically
checkable lives here so no model re-judges it. Red starts these tests when a
new rule joins (docs/adr/0001-cheap-vision-reviewer.md).
"""

from __future__ import annotations

import re
from collections.abc import Callable
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
SCAN_FILES: tuple[Path, ...] = (
    REPO / "static" / "css" / "app.css",
    REPO / "static" / "css" / "input.css",
    *sorted((REPO / "templates").rglob("*.html")),
)

OKLCH = re.compile(r"oklch\(\s*([\d.]+)%?\s+([\d.]+)\s+(-?[\d.]+)", re.I)
HEX = re.compile(r"#([0-9a-fA-F]{6})\b")
NAMED_GREEN = re.compile(
    r"\b(green|lime|emerald|teal|mint|chartreuse|olive)\b", re.I
)
TAILWIND_GREEN = re.compile(
    r"\b(?:text|bg|border|ring|fill|stroke|from|to|via)-(?:green|lime|emerald|teal)-\d{2,3}\b"
)
TAILWIND_RED = re.compile(
    r"\b(?:text|bg|border|ring|fill|stroke|from|to|via)-red-\d{2,3}\b"
)
FONT_STACK = re.compile(r"font-family\s*:\s*([^;}]+)")
ALLOWED_FAMILIES = (
    "ibm plex mono",
    "rajdhani",
    "monospace",
    "mono",
    "menlo",
    "consolas",
)
FONT_VAR = re.compile(r"font-family\s*:\s*var\(--font-[\w-]+\)\s*[;}]?")


def _masked_lines(path: Path) -> list[tuple[int, str]]:
    """Lines with /* ... */ comment bodies blanked, so prose inside comments
    never trips a color scan."""
    text = path.read_text()
    out: list[str] = []
    in_comment = False
    for line in text.splitlines():
        kept: list[str] = []
        i = 0
        while i < len(line):
            if in_comment:
                end = line.find("*/", i)
                if end == -1:
                    break
                in_comment = False
                i = end + 2
            else:
                start = line.find("/*", i)
                if start == -1:
                    kept.append(line[i:])
                    break
                kept.append(line[i:start])
                in_comment = True
                i = start + 2
        out.append("".join(kept))
        if in_comment:
            out[-1] = ""
    return list(enumerate(out, 1))


def _oklch_is_green(_lightness: float, c: float, h: float) -> bool:
    return c > 0.02 and 90 <= h < 170


def _oklch_is_red(_lightness: float, c: float, h: float) -> bool:
    return c > 0.05 and (h >= 350 or h < 50)


def _hex_is_green(hex6: str) -> bool:
    r, g, b = (int(hex6[i : i + 2], 16) for i in (0, 2, 4))
    return g > r + 30 and g > b + 30


def _hex_is_red(hex6: str) -> bool:
    r, g, b = (int(hex6[i : i + 2], 16) for i in (0, 2, 4))
    # Red means r dominant with green and blue comparable; amber (#ffb000)
    # also has r dominant but blue far below green, so it never counts.
    return r > g + 40 and r > b + 40 and abs(g - b) < 40


def _scan(
    matchers: list[tuple[re.Pattern[str], Callable[..., bool] | None]],
) -> list[str]:
    """Every place a forbidden pattern appears, with file:line evidence.
    CSS comments are masked: prose there is documentation, not styling."""
    found: list[str] = []
    for path in SCAN_FILES:
        for n, line in _masked_lines(path):
            for pattern, classify in matchers:
                for m in pattern.finditer(line):
                    if classify is None:
                        matched = True
                    else:
                        matched = classify(*m.groups())
                    if matched:
                        rel = path.relative_to(REPO)
                        found.append(
                            f"{rel}:{n}: {m.group(0)!r} in {line.strip()!r}"
                        )
    return found


def test_no_green_anywhere() -> None:
    """No green "success" color: OK is amber, broken is red (design.md)."""
    found = _scan([
        (
            OKLCH,
            lambda lig, c, h: _oklch_is_green(float(lig), float(c), float(h)),
        ),
        (HEX, _hex_is_green),
        (NAMED_GREEN, None),
        (TAILWIND_GREEN, None),
    ])
    assert not found, (
        "green found (OK is amber, broken is red):\n" + "\n".join(found)
    )


def test_red_appears_only_on_alert_lines() -> None:
    """Red is reserved for errors and alerts, never decoration. A red color
    literal is allowed only where the line itself says alert."""
    found: list[str] = []
    for path in SCAN_FILES:
        for n, line in _masked_lines(path):
            if "alert" in line.lower():
                continue
            hits = (
                any(
                    _oklch_is_red(float(lig), float(c), float(h))
                    for lig, c, h in OKLCH.findall(line)
                )
                or any(_hex_is_red(h) for h in HEX.findall(line))
                or TAILWIND_RED.search(line)
            )
            if hits:
                rel = path.relative_to(REPO)
                found.append(f"{rel}:{n}: {line.strip()!r}")
    assert not found, "red outside alert contexts:\n" + "\n".join(found)


def test_only_the_two_fonts() -> None:
    """Body: IBM Plex Mono. Display: Rajdhani. No third family. Stacks may
    go through --font-* variables; the variable definitions are judged too."""
    found: list[str] = []
    for path in SCAN_FILES:
        for n, line in _masked_lines(path):
            if FONT_VAR.search(line):
                continue
            for stack in FONT_STACK.findall(line):
                lowered = stack.lower()
                if not any(f in lowered for f in ALLOWED_FAMILIES):
                    rel = path.relative_to(REPO)
                    found.append(f"{rel}:{n}: {stack.strip()!r}")
    assert not found, "unknown font family:\n" + "\n".join(found)
