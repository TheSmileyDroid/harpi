"""The design review gate: fails until a fresh, passing verdict exists.

Wired into ``make check`` (see docs/adr/0001-cheap-vision-reviewer.md). The
verdict is produced by the design review (tools/design_review.py captures
the shots; the reviewer judges them) and must carry the digest of the UI
surfaces it judged. A missing, stale, failing, or malformed verdict is a red
gate: fix the cause, never lower the bar.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
VERDICT_PATH = REPO / ".scratch" / "design-review" / "verdict.json"


def _display(verdict_path: Path) -> str:
    try:
        return str(verdict_path.relative_to(REPO))
    except ValueError:
        return str(verdict_path)


def check(verdict_path: Path, digest: str) -> str | None:
    """Return the reason the gate is red, or None when it passes."""
    where = _display(verdict_path)
    if not verdict_path.is_file():
        return (
            "design review required: no verdict at "
            f"{where}. Run "
            "`uv run python tools/design_review.py`, judge the shots, write "
            "the verdict (see .opencode/skills/design-review/)."
        )
    try:
        verdict = json.loads(verdict_path.read_text())
    except json.JSONDecodeError:
        return (
            "design review gate red: verdict is unreadable JSON at "
            f"{where}. Rewrite it per the skill."
        )
    if (
        not isinstance(verdict, dict)
        or "digest" not in verdict
        or "overall" not in verdict
    ):
        return (
            "design review gate red: verdict is missing 'digest' or "
            f"'overall' in {where}."
        )
    if verdict["digest"] != digest:
        return (
            f"design review gate red: verdict is stale (it covers digest "
            f"{verdict['digest']}, the UI is now {digest}). Re-run "
            "`uv run python tools/design_review.py` and review again."
        )
    if verdict["overall"] != "pass":
        return (
            "design review gate red: the last design review found failures. "
            f"See {where}; fix the flagged items "
            "and review again."
        )
    return None


def main() -> int:
    # Running as a script puts tools/ on sys.path, not the repo root.
    sys.path.insert(0, str(REPO))
    from tools.design_review import ui_digest

    reason = check(VERDICT_PATH, ui_digest())
    if reason is not None:
        print(reason, file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
