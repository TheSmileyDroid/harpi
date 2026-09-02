# Spec: Apply the panel design language

Status: ready-for-agent

## Problem Statement

The panel's look grew ad hoc: an early amber terminal theme with parts of the target aesthetic already present, but drifting. `docs/agents/design.md` now records the design language the maintainer chose (TVA CRT as the soul, Cyberpunk 2077 as the structural grammar), yet the actual panel still uses the old fonts, the old background, brackets on every panel, and no Cyberpunk grammar. Anyone editing the panel has no way to know whether the page on screen actually matches the documented language.

## Solution

Bring the panel into conformance with `docs/agents/design.md`: swap the type stack, retune the color tokens, correct the bracket rule, and apply the Cyberpunk grammar to lists and action strips. While implementing, the agent visually verifies the running panel in a real browser using the `/playwriter` skill, so design decisions are judged against rendered pixels, not imagination.

The source of truth for every visual decision is `docs/agents/design.md`. Where this spec and the doc disagree, the doc wins.

## User Stories

1. As a panel user, I want body text set in IBM Plex Mono, so that dense telemetry reads comfortably in a CRT-flavored mono.
2. As a panel user, I want titles, panel headers, and labels set in Rajdhani semibold uppercase with wide tracking, so that the panel speaks with the Cyberpunk menu voice.
3. As a panel user, I want a near-black neutral background, so that the amber reads as glowing phosphor instead of washed-out beige.
4. As a panel user, I want amber as the only accent color, so that the panel has one visual language.
5. As a panel user, I want red to appear only on errors and alerts, so that seeing red always means something is broken.
6. As a panel user, I want the OK state (bot online, playing) rendered in amber, so that success needs no second color.
7. As a panel user, I want subtle global scanlines and a vignette, so that the screen feels like a tube without distracting from content.
8. As a panel user, I want no flicker, curvature, or per-element glow, so that long sessions don't fatigue my eyes.
9. As a panel user, I want double 1px borders (inner `line`, outer `line-strong`) on panels and boxed titles, so that surfaces read as TVA console frames.
10. As a panel user, I want corner brackets only on the element currently focused or active, so that a bracket tells me what is under operation right now.
11. As a panel user, I want no brackets on resting panels, so that brackets stay meaningful.
12. As a panel user, I want list rows with metadata (author, status, timestamp) in a right-hand column, so that I can scan state without reading each row.
13. As a panel user, I want a card's actions in a segmented strip along its bottom edge, so that commands read as a console control row.
14. As a panel user, I want a subtle global loading indicator during HTMX activity, so that I know the panel is alive without skeletons strobing on the 2s status poll.
15. As a panel user, I want `hx-indicator` feedback on the button I just pressed, so that my action visibly registered.
16. As a panel user, I want polling swaps to be visually silent when nothing changed, so that the panel doesn't blink at me every 2 seconds.
17. As a panel user, I want view transitions between pages (already present, kept), so that navigation feels like one console.
18. As a panel user, I want no boot animation on appearing elements, so that polling fragments don't replay an entrance forever.
19. As a mobile panel user, I want a single column with reduced chrome but the same design language, so that the console identity survives small screens.
20. As a maintainer, I want all tokens defined in one place and compiled by the existing Tailwind build, so that the palette can't fork.
21. As a maintainer, I want the type stack limited to two families, so that the design system stays small.
22. As a maintainer, I want the implementer to screenshot and inspect the live panel while working, so that visual regressions are caught during the change, not after.

## Implementation Decisions

- `docs/agents/design.md` is normative; read it first. This spec schedules the migration; the doc defines the target.
- Color tokens: adopt the token table from the design doc (background, surface, surface-2, line, line-strong, primary, amber-bright, amber-dim, idle, alert, alert-dim) in the Tailwind theme source file. Hue 85 stays the base; alert keeps hue 27.
- Type stack: body moves to IBM Plex Mono, display moves to Rajdhani (semibold, uppercase, tracking). Fira Code and Share Tech Mono leave the font imports and theme variables. Google Fonts link in the layout is updated accordingly, with system mono fallbacks.
- Bracket rule: remove brackets from the resting panel component; brackets become a state applied to the focused/active element (focus-visible, current nav item, playing row, active control).
- Cyberpunk grammar on lists and action strips: right-hand metadata column in list rows; segmented bottom-edge action strip on cards. Components first: music queue/transport, bot status chip, home page cards.
- Loading: one subtle global indicator (thin top bar or caret, fixed position) plus per-action `hx-indicator`. No skeletons on polling fragments.
- Texture: the global scanline overlay already exists; add the subtle vignette to the same overlay layer. Keep `pointer-events: none` and the `prefers-reduced-motion` guard pattern already in place.
- Mobile: existing single-column collapse stays; verify the new components (action strips, metadata columns) degrade to one column without losing the language.
- The panel is served by the existing Quart app; no backend changes. No new dependencies beyond the two fonts.
- Hard limit: never `make start` — that joins the maintainer's live guild. The visual loop runs **`make dev`** (recommended): the configured token is the test bot's, so the bot connects only to the test guild and live states (status chip, playing track, queue) are real. No fake-token workaround or skip flag is needed.

## Testing Decisions

- Good tests assert rendered external behavior, not CSS internals: which classes and states the HTML carries, not which rules produce them.
- Seam 1 (HTML): Quart test client against the page routes with a fake bot, exactly like the existing index/status page tests. Assert bracket classes are absent at rest, present on the active element, global indicator element exists, red tokens only on error/offline surfaces.
- Seam 2 (build): `make tailwind` compiles the theme source into `app.css`; the gate is a clean build with the new tokens present in the output. Prior art: the Makefile tailwind targets.
- Seam 3 (visual, in-loop): the implementing agent uses `/playwriter` against the running panel (bot enabled with the test token, per the hard-limit decision above) while working. Per session: `playwriter skill` first, then `playwriter session new`, drive the panel (open pages, hover/focus controls, exercise real states: bot status chip, queue with a track playing, transport bar), capture screenshots before/after each component change, and use computed-style checks for token conformance (colors, font-family, bracket presence). These are working-session checks, not committed pytest tests; a finding that should be permanent becomes either a Seam 1 assertion or a note on the issue.
- Visual fidelity judgment (does it *feel* TVA + Cyberpunk) is human review against the reference images at the end; the agent's playwriter loop catches mechanical violations, not taste.

## Out of Scope

- New pages or new panel features (queue redesign beyond restyle, new surfaces).
- A committed browser-test suite (playwright/playwriter in CI) — separate spec if wanted.
- Any cyan, steel blue, or hologram decoration from the rejected reference images.
- The Discord command surface; commands and panel are one feature, but this spec only touches the visual surface.
- Dark/light theme switching — the console has one mode.

## Further Notes

- Reference images live in `references/`; the two that matter are the TVA terminal shots and the Cyberpunk menu screenshot.
- The current CSS already contains scanlines, view transitions, and a caret blink — keep what conforms, correct what doesn't; this is a conformance pass, not a rewrite.
- Rollout order suggestion: tokens + fonts first (one commit), then bracket rule, then components one by one with playwriter verification each step.
