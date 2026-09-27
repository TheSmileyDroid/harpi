---
name: Harpi
description: One process, one panel — an amber-phosphor CRT console for a Discord bot.
colors:
  background: "oklch(12% 0.004 85)"
  surface: "oklch(16% 0.008 85)"
  surface-2: "oklch(20% 0.01 85)"
  line: "oklch(32% 0.02 85)"
  line-strong: "oklch(48% 0.03 85)"
  primary: "oklch(80% 0.14 85)"
  amber-bright: "oklch(88% 0.11 88)"
  amber-dim: "oklch(63% 0.08 85)"
  idle: "oklch(48% 0.005 85)"
  alert: "oklch(67% 0.19 27)"
  alert-dim: "oklch(45% 0.12 27)"
typography:
  display:
    fontFamily: "Rajdhani, IBM Plex Mono, ui-monospace, monospace"
    fontSize: "1.25rem"
    fontWeight: 600
    letterSpacing: "0.2em"
  headline:
    fontFamily: "Rajdhani, IBM Plex Mono, ui-monospace, monospace"
    fontSize: "1rem"
    fontWeight: 600
    letterSpacing: "0.3em"
  title:
    fontFamily: "Rajdhani, IBM Plex Mono, ui-monospace, monospace"
    fontSize: "0.8rem"
    fontWeight: 600
    letterSpacing: "0.15em"
  body:
    fontFamily: "IBM Plex Mono, ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, Liberation Mono, Courier New, monospace"
    fontWeight: 400
    lineHeight: 1.5
  label:
    fontFamily: "Rajdhani, IBM Plex Mono, ui-monospace, monospace"
    fontSize: "0.7rem"
    fontWeight: 600
    letterSpacing: "0.2em"
  tab:
    fontFamily: "Rajdhani, IBM Plex Mono, ui-monospace, monospace"
    fontSize: "0.75rem"
    fontWeight: 600
    letterSpacing: "0.15em"
  micro:
    fontFamily: "IBM Plex Mono, ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, Liberation Mono, Courier New, monospace"
    fontSize: "0.65rem"
    fontWeight: 400
    letterSpacing: "0.1em"
rounded:
  none: "0px"
spacing:
  xs: "0.35rem"
  sm: "0.5rem"
  md: "0.75rem"
  lg: "1rem"
  xl: "1.25rem"
components:
  button-primary:
    backgroundColor: "transparent"
    textColor: "{colors.primary}"
    typography: "{typography.title}"
    rounded: "{rounded.none}"
    padding: "0.45rem 1.1rem"
  button-primary-hover:
    backgroundColor: "{colors.primary}"
    textColor: "{colors.background}"
  button-danger:
    backgroundColor: "transparent"
    textColor: "{colors.alert}"
    typography: "{typography.title}"
    rounded: "{rounded.none}"
    padding: "0.45rem 1.1rem"
  button-danger-hover:
    backgroundColor: "{colors.alert}"
    textColor: "{colors.background}"
  input-text:
    backgroundColor: "transparent"
    textColor: "{colors.primary}"
    typography: "{typography.body}"
    rounded: "{rounded.none}"
    padding: "0.35rem 0.6rem"
  panel:
    backgroundColor: "{colors.surface}"
    rounded: "{rounded.none}"
    padding: "1rem"
  panel-label:
    backgroundColor: "{colors.surface-2}"
    textColor: "{colors.primary}"
    typography: "{typography.label}"
    rounded: "{rounded.none}"
    padding: "0.15rem 0.6rem"
  nav-main:
    textColor: "{colors.amber-dim}"
    typography: "{typography.title}"
  toast:
    backgroundColor: "{colors.surface}"
    textColor: "{colors.primary}"
    rounded: "{rounded.none}"
    padding: "0.35rem 0.6rem"
---

# Design System: Harpi

## Overview

**Creative North Star: "The Cyberpunk Menu Grammar, clad in a TVA Terminal"**

Harpi's panel is warm amber nostalgia made operational. The material is a
phosphor CRT: a near-black tube that glow sits on, scanlines drawn over
everything as one fixed layer, double 1px frames around anything that holds
content. The structure is Cyberpunk 2077's menu grammar: thin lines, small
caps with wide tracking, metadata collected in a right-hand column, actions
segmented into a strip along a card's bottom edge. Nothing skeuomorphic, no
curvature, no flicker, no per-element glow — the tube is felt, not simulated.

Density is the point. The whole surface reads as one console with a telemetry
voice, Home included: labels are small caps, numbers appear anywhere a state
can be read, and rows pack thumbnail, index, title, and metadata onto one
line. Confirmed rejections: no cyan, no steel blue, no full-hologram
decoration (the rejected direction candidates in `references/`), no green
success color, no third font family.

The binding commitment from PRODUCT.md holds: the CRT retro theme is Harpi's
identity. Future work extends this world, never replaces it.

**Key Characteristics:**
- Amber phosphor on near-black; red reserved exclusively for broken things
- Two families: IBM Plex Mono body, Rajdhani semibold uppercase display
- Zero radius everywhere; 1px lines only, never thick borders
- Depth from double borders and tonal steps, never shadows
- Corner brackets mark only the element under operation right now

## Colors

One accent dominates the whole panel: amber, warm and glowing against a tube
that is nearly off, with red held in reserve for failure.

### Primary
- **Phosphor Amber** (`oklch(80% 0.14 85)`): main ink. Values, titles, button
  text, progress fill, meter fill — anywhere state is read normally.
- **Hot Amber** (`oklch(88% 0.11 88)`): the element under operation one step
  above normal text. Caret block after the page title, focus brackets, the
  active nav/tab underline, the HTMX indicator bar, a highlighted search row.
- **Ember Amber** (`oklch(63% 0.08 85)`): secondary text. Data labels, subtitles,
  row metadata, readouts, idle (paused) progress. Holds 4.5:1 on `surface`
  and above on the page background.

### Neutral
- **Tube Black** (`oklch(12% 0.004 85)`): page background. Near-black with a
  faint warm lean; an amber-tinted background would dilute the accent.
- **Panel Charcoal** (`oklch(16% 0.008 85)`): panel interior (`surface`).
- **Raised Charcoal** (`oklch(20% 0.01 85)`): hover and secondary chrome —
  boxed title plates, active row tint, action strips (`surface-2`).
- **Dim Line** (`oklch(32% 0.02 85)`): default 1px border, inner line of the
  double frame, separators, meter and slider tracks (`line`).
- **Bright Line** (`oklch(48% 0.03 85)`): outer line of the double frame,
  toast border, status chip border (`line-strong`).
- **Ash Gray** (`oklch(48% 0.005 85)`): disabled text and empty readouts
  (`idle`). Its low contrast is intentional and must not leak into readable
  content.

### Tertiary
- **Signal Red** (`oklch(67% 0.19 27)`): errors and alerts only — panel error
  text, offline chip, danger button ink (`alert`). Clears 4.5:1 on
  `surface`, where error text and danger buttons sit.
- **Deep Signal** (`oklch(45% 0.12 27)`): borders of alert elements and the
  danger button at rest (`alert-dim`).

### Named Rules
**The Red Means Broken Rule.** Red appears only when something is broken or
being destroyed. If red shows up for a non-alert reason, fix the usage, not
the rule. There is no green success color: OK is amber, broken is red.

**The One-Step Rule.** `amber-bright` glows exactly one step above
`primary`, and only on the element under operation right now — caret, focus
bracket, active underline, highlighted row. Never a whole sentence, never a
background.

## Typography

**Display Font:** Rajdhani (with IBM Plex Mono as fallback)
**Body Font:** IBM Plex Mono (with ui-monospace, Menlo, Consolas, Courier New fallbacks)

**Character:** A machine that speaks in warm light. IBM Plex Mono carries the
dense telemetry body; Rajdhani semibold, uppercase, wide-tracked, carries
every title, label, and control — the Cyberpunk UI voice. Loaded at weights
400/600 (Mono) and 600 (Rajdhani) only.

### Hierarchy
- **Display / page title** (600, 1.25rem, tracking 0.2em): page headings in
  Rajdhani uppercase, Phosphor Amber, trailed by a blinking block caret.
- **Headline / logo** (600, 1rem, tracking 0.3em): the wordmark only.
- **Title / nav and control** (600, 0.8rem, tracking 0.15em, uppercase):
  main nav, side tabs, buttons — Ember Amber at rest, Phosphor Amber on
  hover, Hot Amber when current.
- **Body** (400, 1rem default, line-height 1.5): IBM Plex Mono. Panel rows
  compress to 0.8rem, metadata and readouts to 0.7rem, micro-labels to
  0.65rem — density comes from these steps, not from a fourth family.
- **Label** (600, 0.7rem, tracking 0.2em, uppercase): boxed panel titles
  (`panel-label`) in Rajdhani. Data labels (`data-label`) are the mono
  counterpart: 0.65rem, tracking 0.1em, uppercase, Ember Amber. Boxed panel
  titles take Phosphor Amber: on their `surface-2` plate Ember misses 4.5:1.

### Named Rules
**The Two-Family Rule.** IBM Plex Mono and Rajdhani, nothing else. A third
family breaks the console.

**The Small-Caps Rule.** Anything that labels rather than reads — nav, tabs,
buttons, panel titles, data keys, toasts — is uppercase with wide tracking.
Sentence case is reserved for content values and confirm sentences.

## Layout

Single column that splits once. The app shell (`.app-container`) pads
0.5rem top, 1.25rem sides, and reserves 5.5rem at the bottom for the fixed
chrome; consecutive blocks in the main column stack with a 1rem gap.

The Music page is the only split layout: a two-column grid (fluid main
column + fixed 20rem side rail) above 48rem (768px), single column below.
Panel interiors pad 1rem; the boxed title plate sits 0.75rem above panel
content.

Fixed chrome stacks from the bottom: status strip at the very bottom
(0.75rem tall band), transport bar 1.75rem above the viewport bottom,
toasts anchored 3rem up on the right. Content padding grows to 10rem on
mobile where the transport wraps.

Breakpoints (observed): 30rem (480px) collapses the header to wrapped rows,
stacks row metadata, and stacks action strips vertically; 48rem (768px)
enables the Music two-column grid. The design language never switches off at
either — density collapses, identity stays.

Spacing rhythm: 0.35rem inside rows, 0.5rem between related controls, 0.75rem
between a label and its content, 1rem between panels, 1.25rem page gutters.

## Elevation & Depth

The system is flat. There are no drop shadows anywhere; depth is conveyed by
three structural moves: the double 1px frame (inner `line` border plus
`line-strong` outline 2px outside it), the three-step tonal ladder
(background → surface → surface-2), and 1px separators that segment strips
and rows. The only non-flat treatments in the whole stylesheet are an inset
1px amber underline marking the active search row and the dialog backdrop
dimming the tube.

### Shadow Vocabulary
- None. Zero `box-shadow` values are used for elevation.

### Named Rules
**The Flat-By-Default Rule.** Surfaces are flat at rest. If a new surface
seems to need a shadow, give it the double frame or a tonal step instead.

## Shapes

Square corners everywhere: radius is 0px on every element, enforced by the
base reset and maintained by every component (the range slider thumb is a
3px × 12px rectangle, the progress fill is a hard-edged bar). Borders are
1px only — thick borders have no place in this grammar. Frames come in two
flavors: single 1px (`line`) for rows, inputs, thumbnails; double (1px
`line` + 1px `line-strong` outline offset 2px) for panels, boxed titles, the
now-playing art, the search dropdown. The recurring silhouette is the corner
bracket: two 0.75rem L-shapes in Hot Amber sitting on the corners of the
element under operation.

## Components

The panel's controls are tactile and confident: flat 1px-outlined rectangles
that invert to solid amber under the cursor, uppercase Rajdhani labels, and
segmented strips that make a card's actions feel like a row of physical
keys.

### Buttons
- **Shape:** square (0px radius), 1px `amber-dim` border, min-width 4.5rem,
  padding 0.45rem 1.1rem.
- **Primary:** transparent background, Phosphor Amber text, Rajdhani 600 at
  0.72rem, tracking 0.12em, uppercase, line-height 1.
- **Hover / Focus:** hover inverts to solid Phosphor Amber on Tube Black.
  Focus-visible swaps the border for Hot Amber corner brackets (0.75rem L
  shapes). While an HTMX request is in flight the button blinks Hot Amber
  (0.8s steps) — per-action feedback, no skeletons.
- **Danger:** identical structure in Signal Red ink with `alert-dim` border;
  hover inverts to solid Signal Red. Reserved for destructive actions.
- **Ghost / tab:** `.side-tab` and nav links have no border at rest; hover
  lifts text from Ember to Phosphor Amber.

### Chips
- **Status chip (`bot-online` / `bot-offline`):** Rajdhani 600, tracking
  0.15em, padding 0.1rem 0.4rem, 1px border. Online = Phosphor Amber on
  `line-strong`. Offline = Signal Red on `alert` border, blinking at 1s
  steps. This is the only red that blinks for state rather than action.

### Cards / Containers
- **HUD panel:** the one container. Surface background, padding 1rem, double
  frame (1px `line` border, 1px `line-strong` outline at 2px offset).
- **Boxed title (`panel-label`):** Rajdhani label plate on `surface-2`, its
  own double frame, sitting inline at the panel's top — numbered like
  `01 // NOW PLAYING`. Ink is Phosphor Amber: Ember Amber cannot hold 4.5:1
  on raised charcoal.
- **Action strip:** the card's bottom edge. Full-bleed (negative margins to
  the panel edges), `surface-2` background, 1px top border, buttons divided
  by 1px `line` separators, right-aligned. Dialog strips keep the panel
  `surface` instead, so Signal Red danger ink clears 4.5:1 at rest.
- **Playing state:** a panel carrying `.is-playing` grows Hot Amber corner
  brackets — the panel under operation right now.

### Inputs / Fields
- **Style:** transparent background, 1px `line` border, Phosphor Amber text,
  0.8rem, padding 0.35rem 0.6rem, square. Selects share the class.
- **Focus:** border replaced by Hot Amber corner brackets on the field.
- **Placeholder:** Ash Gray (disabled ink) — placeholders are not content.

### Navigation
- **Main nav:** Rajdhani 600, 0.8rem, tracking 0.15em, uppercase, Ember
  Amber, items 1.25rem apart. Hover lifts to Phosphor Amber with an Ember
  underline; the current page (`aria-current="page"`) is Hot Amber with a
  Hot Amber 1px underline. Never a box, never brackets — nav-sized text in
  brackets reads as a box.
- **Side tabs:** same grammar one size down (0.75rem), sitting on a 1px
  `line` bottom border that the active tab's underline replaces.

### Signature Components
- **CRT overlay:** one fixed pseudo-element layer over the whole viewport —
  repeating 1px scanlines at 12% black every 3px plus a vignette fading to
  35% black at the edges. Pointer-events none, no flicker, no curvature.
- **Corner brackets:** the focus language. 0.75rem L-shapes in Hot Amber on
  focus-visible buttons/inputs, the focused volume control, and the playing
  panel. A bracket means "under operation right now", nothing else.
- **Global indicator:** a 2px Hot Amber bar fixed to the viewport top during
  user-initiated HTMX requests, animating scaleX 0.1 → 1 over 1.2s. Pollers
  never trip it.
- **Blinking caret:** `▌` after the page title in Ember Amber, 1.2s
  steps(2) — the terminal cursor.
- **Toast:** fixed column bottom-right, surface background, `line-strong`
  border with a 1px Phosphor Amber left edge, uppercase mono 0.7rem. Amber
  only, confirmations only — errors never arrive here.
- **Panel error:** persistent 1px `alert` box, Signal Red text, 0.75rem.
  Stays until the server re-renders it away.

## Do's and Don'ts

### Do:
- **Do** keep every corner square (0px radius) and every border 1px.
- **Do** frame panels with the double line: 1px `line` border + 1px
  `line-strong` outline at 2px offset.
- **Do** put corner brackets only on the element under operation right now
  (keyboard focus, focused volume control, playing panel).
- **Do** mark the current nav or tab item with Hot Amber text plus a 1px
  underline — no box.
- **Do** uppercase and wide-track every label, title, tab, and button
  (Rajdhani, tracking 0.12em–0.3em).
- **Do** collect list-row metadata into a right-hand `.row-meta` column.
- **Do** seat a card's actions in a segmented strip along its bottom edge.
- **Do** render red for errors and destructive actions only, and keep errors
  persistent in `#panel_error`.
- **Do** keep the single scanline/vignette overlay as one fixed layer above
  content.

### Don't:
- **Don't** use red for anything that is not broken or being destroyed, and
  never introduce a green success color — OK is amber.
- **Don't** add a third font family, or set body copy in anything but IBM
  Plex Mono.
- **Don't** add drop shadows, glows, flicker, curvature, or per-element
  neon.
- **Don't** put brackets around nav-sized text; use the underline.
- **Don't** pull cyan, steel blue, or hologram decoration from the rejected
  `references/` candidates.
- **Don't** use thick borders, rounded corners, badges/flags, or skeletons
  on polled fragments.
- **Don't** let Ash Gray (`idle`) leak into readable content.
- **Don't** give background pollers any visible loading treatment; the 2s
  status polls must stay visually silent.
