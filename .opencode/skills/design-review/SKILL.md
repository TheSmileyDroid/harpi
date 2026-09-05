---
name: design-review
description: "The design review: judge panel work against docs/agents/design.md and write the verdict the make check gate demands. Use when panel files changed (pages/, templates/, static/css/), when make check says 'design review required' or 'verdict is stale', before declaring panel work done, or when asked for a design review or verdict."
---

# Design review

Judge the panel the way design.md says it must look, and write the verdict that gates `make check` (docs/adr/0001-cheap-vision-reviewer.md). The split: every rule a test can judge is already a test (`tests/test_design_language.py`) — you add nothing there. You judge only what pixels reveal.

## Steps

1. **Capture.** Run `uv run python tools/design_review.py`. It serves the panel offline with fakes (never the real bot), shoots Home and Music at 1280 and 375, full-page and viewport-height, and prints `DIGEST:`. The shots land in `.scratch/design-review/shots/`.
2. **Judge.** View all eight shots. For each item below, decide `pass`, `fail`, or `inapplicable` and collect evidence (which shot, which element, where on the page).
3. **Write the verdict** to `.scratch/design-review/verdict.json` (schema below), carrying the exact digest from step 1.
4. **Fail loud.** On any `fail` item: fix the cause, re-capture, re-judge, at most two rounds. Still failing? Stop and surface the verdict and the shots to the human. Never lower a checklist item, never widen an interpretation to pass. A red gate beats a false green.

## Checklist

- **V1 Contrast.** Labels, secondary text, and dim states stay readable against the near-black background. `idle` gray appears only on disabled things.
- **V2 Amber dominance.** The page reads as amber phosphor on dark. Red appears only where something is broken. (No green anywhere — that part is already a test.)
- **V3 Brackets mark operation.** Two ornaments live near panel corners; do not confuse them. A **boxed title** is the double-bordered chip around a panel label (`00 // LINK`, `02 // QUEUE`); every panel has one and it is always allowed. A **corner bracket** is a bright L-shaped mark sitting ON the panel's outer frame corner, brighter and thicker than the border line; it glows against the frame the way a caret glows against text. Corner brackets sit only on the element under operation right now: the playing panel (`.is-playing`) and focus states. Anywhere else, including as decoration on static panels, is a fail. Nav items never get brackets; the current one brightens with a 1px underline.
- **V4 Console rhythm.** Dense, aligned panels; boxed titles line up; list rows carry their metadata in a right-hand column; card actions sit in a segmented bottom strip.
- **V5 Mobile holds identity.** At 375: single column, reduced chrome, and the same design language — no element orphaned, scattered, or re-styled into a different app.
- **V6 Nothing collides.** No element cut off, overlapping another, or covering a control at either width. Judge the fixed transport bar on the viewport-height shot, not the full-page one: full-page captures paint fixed bars at the scroll seam.
- **V7 Fidelity holds.** Scanlines barely perceptible, no per-element glow, no HUD excess, no badges.

## Verdict schema

```json
{
  "digest": "<the DIGEST from capture>",
  "overall": "pass",
  "reviewed_at": "<ISO date>",
  "model": "<who judged this, e.g. mimo-2.5 or human:gf>",
  "items": [
    {"id": "V1", "status": "pass", "evidence": "one line: what you saw, in which shot, where"}
  ]
}
```

`overall` is `fail` the moment any item fails. The gate (`tools/design_review_gate.py`) re-computes the digest of `pages/`, `templates/`, `static/css/`, this skill, and `docs/agents/design.md`; any byte that changed makes the verdict stale and `make check` red again. The capture tool itself is not hashed: tooling changes do not re-open a review. That is the point.
