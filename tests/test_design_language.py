"""The design language rules a test can judge (DESIGN.md).

Everything mechanically checkable lives here. Red starts these tests when a
new rule joins.
"""

from __future__ import annotations

import re
from collections.abc import Callable
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
SCAN_FILES: tuple[Path, ...] = (
    REPO / "web" / "src" / "app.css",
    *sorted((REPO / "web" / "src").rglob("*.svelte")),
)

OKLCH = re.compile(r"oklch\(\s*([\d.]+)%?\s+([\d.]+)\s+(-?[\d.]+)", re.I)
HEX = re.compile(r"#([0-9a-fA-F]{6})\b")
NAMED_GREEN = re.compile(
    r"\b(green|lime|emerald|teal|mint|chartreuse|olive)\b", re.I
)
FONT_STACK = re.compile(r"font-family\s*:\s*([^;}]+)")
ALLOWED_FAMILIES = (
    "urbanist",
    "barlow",
    "jetbrains mono",
    "liberation mono",
    "menlo",
    "monaco",
    "consolas",
)
ALLOWED_GENERICS = (
    "ui-monospace",
    "sfmono-regular",
    "monospace",
    "mono",
    "system-ui",
    "sans-serif",
)
FONT_VAR = re.compile(r"font-family\s*:\s*var\(--font-[\w-]+\)\s*[;}]?")
FONT_TOKEN = re.compile(r"--font-[\w-]+\s*:\s*([^;]+);", re.S)
RADIUS = re.compile(r"\b[a-z-]*radius\s*:\s*([^;}]+)")
RADIUS_TOKEN = re.compile(r"--radius-[\w-]+\s*:\s*([^;]+);")
CUT_RADII = (
    "0",
    "0px",
    "1px",
    "2px",
    "3px",
    "4px",
    "var(--radius-key)",
    "var(--radius-plate)",
)


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
    """No green anywhere: amber marks state and every live reading, sand is
    the material of what the operator presses, and red is reserved for
    breakage (DESIGN.md)."""
    found = _scan([
        (
            OKLCH,
            lambda lig, c, h: _oklch_is_green(float(lig), float(c), float(h)),
        ),
        (HEX, _hex_is_green),
        (NAMED_GREEN, None),
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
            hits = any(
                _oklch_is_red(float(lig), float(c), float(h))
                for lig, c, h in OKLCH.findall(line)
            ) or any(_hex_is_red(h) for h in HEX.findall(line))
            if hits:
                rel = path.relative_to(REPO)
                found.append(f"{rel}:{n}: {line.strip()!r}")
    assert not found, "red outside alert contexts:\n" + "\n".join(found)


def _unknown_families(stack: str) -> list[str]:
    """Families named in one font stack that are neither the two faces nor
    the fallback generics, quoted or not."""
    found: list[str] = []
    for item in stack.split(","):
        family = item.strip().strip("\"'").lower()
        if not family:
            continue
        if family in ALLOWED_FAMILIES or family in ALLOWED_GENERICS:
            continue
        found.append(family)
    return found


def test_only_the_three_faces() -> None:
    """Legends: Urbanist. Labels: Barlow. Values: JetBrains Mono, and
    nothing else. Stacks may go through --font-* variables; literal stacks
    are judged here."""
    found: list[str] = []
    for path in SCAN_FILES:
        for n, line in _masked_lines(path):
            if FONT_VAR.search(line):
                continue
            for stack in FONT_STACK.findall(line):
                rel = path.relative_to(REPO)
                found.extend(
                    f"{rel}:{n}: {family!r} in {stack.strip()!r}"
                    for family in _unknown_families(stack)
                )
    assert not found, "unknown font family:\n" + "\n".join(found)


def test_font_variables_name_only_the_three_faces() -> None:
    """The --font-* tokens are the real stacks; judge every family they
    name, quoted or not, against the three faces plus the generics."""
    path = REPO / "web" / "src" / "app.css"
    text = "\n".join(line for _, line in _masked_lines(path))
    found: list[str] = []
    for stack in FONT_TOKEN.findall(text):
        found.extend(
            f"{path.name}: {family!r} in {stack.strip()!r}"
            for family in _unknown_families(stack)
        )
    assert not found, "unknown font family in a --font-* token:\n" + "\n".join(
        found
    )


def test_corners_stay_cut() -> None:
    """A corner is cut, never rounded: 1px on stamps and lamps, 2px on
    instrument bits, 3px on keys and 4px on plates. Pills and circles are
    the category default, not this world (DESIGN.md). Every radius property
    is judged, logical longhands included."""
    found: list[str] = []
    for path in SCAN_FILES:
        for n, line in _masked_lines(path):
            for value in RADIUS.findall(line):
                if value.strip() not in CUT_RADII:
                    rel = path.relative_to(REPO)
                    found.append(f"{rel}:{n}: {value.strip()!r}")
    assert not found, "rounded corner outside the cut radii:\n" + "\n".join(
        found
    )


def test_corner_tokens_stay_small() -> None:
    """The two radius tokens are the whole ladder: keys 3px, plates 4px."""
    path = REPO / "web" / "src" / "app.css"
    text = "\n".join(line for _, line in _masked_lines(path))
    found: list[str] = []
    for value in RADIUS_TOKEN.findall(text):
        pixels = re.fullmatch(r"\s*(\d+(?:\.\d+)?)px\s*", value)
        if pixels is None or float(pixels.group(1)) > 4:
            found.append(f"{path.name}: {value.strip()!r}")
    assert not found, "corner token above 4px:\n" + "\n".join(found)
