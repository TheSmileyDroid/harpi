# Panel design language

How the Harpi panel looks and behaves. Read before editing `templates/`, `pages/`, or `static/css/`. Reference images live in `references/`.

## North stars

- **Primary: TVA terminal** (`references/ce9c7c4a61c7c3c5bf4bb8dea9c4371b.jpg`, `references/c19b4f13c2d19d20da121d1d69857fda.jpg`) — amber phosphor CRT: dark tube, double 1px borders, boxed panel titles, mono everywhere.
- **Secondary: Cyberpunk 2077 menus** (`references/64e3002ffe918c14b43da9aaff48f57c.jpg`) — the structural grammar: thin lines, small caps with wide tracking, metadata column on the right of list rows, segmented action strip along a card's bottom edge.

The other images in `references/` are direction candidates we rejected. Do not pull cyan, steel blue, or full-hologram decoration from them.

## Tone

The whole panel is a **console**: telemetry voice, monospaced, dense. This includes Home, not just Music. Labels are small caps with wide letter-spacing; numbers are welcome anywhere a state can be read.

## Color

- One accent: **amber** dominates. **Red is reserved for errors and alerts** — never decoration, never a second accent.
- Background: near-black, neutral with a slight warm lean. Amber reads as glowing phosphor against it; an amber-tinted background dilutes the accent.
- No green "success" color: OK is amber, broken is red. A connected bot status glows amber; an error glows red.

Tokens (Tailwind theme colors in `static/css/app.css`, base hue 85 = amber):

```css
--color-background:   oklch(12% 0.004 85);  /* tube off: near-black, faint warmth */
--color-surface:      oklch(16% 0.008 85);  /* panel */
--color-surface-2:    oklch(20% 0.010 85);  /* raised panel / hover */
--color-line:         oklch(32% 0.020 85);  /* default 1px border */
--color-line-strong:  oklch(48% 0.030 85);  /* outer border of double borders, focus */

--color-primary:      oklch(80% 0.140 85);  /* phosphor amber ~#ffb000, main ink */
--color-amber-bright: oklch(88% 0.110 88);  /* caret, active value, highlight */
--color-amber-dim:    oklch(56% 0.080 85);  /* secondary text, labels */
--color-idle:         oklch(48% 0.005 85);  /* disabled, near-gray */

--color-alert:        oklch(62% 0.190 27);  /* red, errors and alerts only */
--color-alert-dim:    oklch(45% 0.120 27);  /* alert borders/icons */
```

Usage rules:

- `amber-bright` marks the element under operation (bracket, caret) — it glows one step above normal text, never more.
- Double borders pair `line` (inner) with `line-strong` (outer); don't invent ad-hoc border colors.
- `idle` is only for disabled text; its low contrast is intentional and must not leak into readable content.

## Type

- **Body: IBM Plex Mono** — dense readable mono.
- **Display: Rajdhani** — the Cyberpunk UI font. Semibold, uppercase, wide tracking, for titles, panel headers, and labels.
- Two families only. Do not add a third.

## Fidelity: medium CRT

Texture and chrome that say "tube screen" without becoming a fantasy HUD:

- **Global scanlines + subtle vignette** as one fixed overlay layer, barely perceptible. No flicker, no curvature, no per-element glow.
- **Double 1px borders** on panels and boxed titles (TVA).
- **Corner brackets only on the focused/active element** — a bracket means "this is under operation right now", nothing else.

Cyberpunk grammar applied on top:

- 1px lines everywhere; no thick borders.
- List rows carry metadata in a right-hand column (author, status, timestamp).
- A card's actions sit in a segmented strip along its bottom edge.
- No badges/flags ("NEW"-style) — the panel has no inbox surface.

## Behavior (HTMX surface)

- **Loading**: one subtle global indicator (thin bar or cursor) plus per-action `hx-indicator` on the triggering element. Never skeletons on polling fragments — the 2s status poll would strobe.
- **Motion**: view transitions between pages, micro-feedback on hover/press. No "boot" animation on elements that appear — polling would replay it forever.
- Polling swaps must be visually silent when nothing changed.

## Mobile

Single column, reduced chrome, identity intact. Density collapses; the design language does not get switched off.

## Hard rule

Red means something is broken. If red appears anywhere for non-alert reasons, the palette is being misused — fix the usage, not the rule.
