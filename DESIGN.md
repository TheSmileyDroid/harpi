---
name: Harpi
description: A Discord bot control panel as a shortwave receiver locked onto an unmarked signal.
colors:
  ground: "oklch(14% 0.012 250)"
  plate: "oklch(19% 0.016 250)"
  plate-2: "oklch(24% 0.022 250)"
  rail: "oklch(37% 0.07 250)"
  rail-deep: "oklch(28% 0.05 250)"
  line: "oklch(38% 0.03 250)"
  line-strong: "oklch(56% 0.05 250)"
  ink: "oklch(88% 0.11 195)"
  ink-mid: "oklch(78% 0.09 200)"
  ink-dim: "oklch(68% 0.06 205)"
  ink-faint: "oklch(63% 0.045 210)"
  lamp: "oklch(82% 0.15 68)"
  lamp-dim: "oklch(60% 0.11 60)"
  alert: "oklch(70% 0.18 25)"
  alert-dim: "oklch(44% 0.1 25)"
  idle: "oklch(50% 0.02 250)"
  tick-major: "oklch(56% 0.05 250 / 0.72)"
  tick-minor: "oklch(56% 0.05 250 / 0.34)"
  seam: "oklch(56% 0.05 250 / 0.4)"
typography:
  display:
    fontFamily: "Michroma, Chivo Mono, ui-monospace, monospace"
    fontSize: "1.05rem"
    fontWeight: 400
    letterSpacing: "0.18em"
  title:
    fontFamily: "Michroma, Chivo Mono, ui-monospace, monospace"
    fontSize: "0.85rem"
    fontWeight: 400
    letterSpacing: "0.3em"
  band:
    fontFamily: "Michroma, Chivo Mono, ui-monospace, monospace"
    fontSize: "0.8rem"
    fontWeight: 400
    letterSpacing: "0.2em"
  legend:
    fontFamily: "Michroma, Chivo Mono, ui-monospace, monospace"
    fontSize: "0.7rem"
    fontWeight: 400
    letterSpacing: "0.22em"
  control:
    fontFamily: "Michroma, Chivo Mono, ui-monospace, monospace"
    fontSize: "0.7rem"
    fontWeight: 400
    letterSpacing: "0.16em"
  body:
    fontFamily: "Chivo Mono, ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, Liberation Mono, monospace"
    fontSize: "1rem"
    fontWeight: 400
    lineHeight: 1.5
  value:
    fontFamily: "Chivo Mono, ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, Liberation Mono, monospace"
    fontSize: "0.8rem"
    fontWeight: 400
    lineHeight: 1.5
  label:
    fontFamily: "Chivo Mono, ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, Liberation Mono, monospace"
    fontSize: "0.7rem"
    fontWeight: 400
    letterSpacing: "0.14em"
rounded:
  none: "0px"
spacing:
  xs: "0.35rem"
  sm: "0.5rem"
  md: "0.75rem"
  lg: "0.85rem"
  xl: "1rem"
  gutter: "1.25rem"
components:
  key:
    backgroundColor: "{colors.plate-2}"
    textColor: "{colors.ink}"
    typography: "{typography.control}"
    rounded: "{rounded.none}"
    padding: "0.5rem 1.05rem 0.45rem"
  key-hover:
    textColor: "{colors.lamp}"
  key-danger:
    backgroundColor: "{colors.plate-2}"
    textColor: "{colors.alert}"
    typography: "{typography.control}"
    rounded: "{rounded.none}"
    padding: "0.5rem 1.05rem 0.45rem"
  key-danger-hover:
    backgroundColor: "color-mix(in oklab, {colors.alert} 16%, {colors.plate-2})"
    textColor: "{colors.alert}"
  input:
    backgroundColor: "color-mix(in oklab, {colors.ground} 85%, black)"
    textColor: "{colors.ink}"
    typography: "{typography.value}"
    rounded: "{rounded.none}"
    padding: "0.45rem 0.65rem"
  select:
    backgroundColor: "{colors.plate-2}"
    textColor: "{colors.ink}"
    typography: "{typography.value}"
    rounded: "{rounded.none}"
    padding: "0.4rem 0.6rem"
  panel:
    backgroundColor: "{colors.plate}"
    rounded: "{rounded.none}"
    padding: "1rem"
  legend-plate:
    backgroundColor: "{colors.rail-deep}"
    textColor: "{colors.ink}"
    typography: "{typography.legend}"
    rounded: "{rounded.none}"
    padding: "0.25rem 0.7rem 0.2rem 0.6rem"
  status-chip:
    backgroundColor: "{colors.rail-deep}"
    textColor: "{colors.ink}"
    typography: "{typography.control}"
    rounded: "{rounded.none}"
    padding: "0.15rem 0.45rem"
  toast:
    backgroundColor: "{colors.plate-2}"
    textColor: "{colors.ink}"
    typography: "{typography.label}"
    rounded: "{rounded.none}"
    padding: "0.35rem 0.6rem"
  readout-cell:
    textColor: "{colors.ink}"
    typography: "{typography.value}"
    rounded: "{rounded.none}"
    padding: "0.35rem 0 0"
  tuning-strip:
    backgroundColor: "color-mix(in oklab, {colors.ground} 82%, black)"
    rounded: "{rounded.none}"
    height: "1.9rem"
  tuning-fill:
    backgroundColor: "color-mix(in oklab, {colors.ink} 18%, transparent)"
    rounded: "{rounded.none}"
  header-rail:
    backgroundColor: "{colors.rail}"
    rounded: "{rounded.none}"
    padding: "0.45rem 0.6rem"
  transport-dock:
    backgroundColor: "{colors.rail}"
    rounded: "{rounded.none}"
    padding: "0.35rem 0.75rem"
---

# Design System: Harpi

## Overview

**Creative North Star: "UNMARKED CARRIER"**

The panel is a shortwave receiver locked onto one unmarked signal, not a dashboard. The page is a cold graphite ground carrying steel-navy plates: the header rail, the transport dock, and every panel legend are the brighter steel of the shell, while panel interiors sit one step up from the ground. Phosphor-cyan signal ink carries every reading. A sodium dial lamp marks what is locked or live right now: the needle, the playing corner lamp, the title lamp, focus rings, the connected link. Legend plates stamp a plain cyan dot instead, and red is held in reserve for what is broken. Signal red is held in reserve for what is broken or being destroyed.

It refuses the category-default card grid. State lives in ruled calibration scales, legend plates, and lit lamps instead of cards: every panel opens with a tick-ruled calibration edge and a plate that names it, the dock leads with a ruler and carries the tuning strip across its width, and even the lamps are squares. Density is the point: labels are small caps, numbers appear anywhere a state can be read, and a queue row packs index, thumbnail, title, a duration gauge, metadata, and a key onto one line.

Michroma carries the legends (plates, band headings, keys, chips, the wordmark). Chivo Mono carries the values (labels, numbers, metadata, inputs). Every corner is square, every edge a 1px hairline, plate seams the only 2px lines, and depth is tonal rather than shadowed. Motion is arrival and settle, never decoration: lamps step-blink, the calibration edge lights once when the panel locks a signal, log rows arrive with a 0.3rem travel, and every spatial entrance is gated behind a reduced-motion preference (see Motion). Confirmed rejections: the amber CRT world this replaced (Rajdhani and IBM Plex Mono, double frames, corner brackets, solid-fill hover inversion), any green success color, any third font family, drop shadows and glows, rounded corners, circles.

The binding commitment from PRODUCT.md holds: the panel's cyberpunk instrument-console identity (this receiver world) is Harpi's visual direction, and the amber CRT remains its predecessor. Future work extends this world, never replaces it.

**Key Characteristics:**
- Cold graphite ground under steel-navy plates; phosphor-cyan signal ink carries every reading
- Sodium dial lamp only for what is live or locked: needle, playing lamp, title lamp, focus, connected link
- Red only for broken or being destroyed; no green success color exists
- Two families, one weight: Michroma legends, Chivo Mono values
- 0px radius, 1px hairlines, 2px plate seams, ruled tick scales instead of card decoration
- Depth from tonal plates and seams, never drop shadows

## Colors

A cold steel instrument face inked in phosphor cyan, with one sodium lamp for the live moment and red held back for breakage.

### Primary
- **Phosphor Cyan** (`oklch(88% 0.11 195)`): the signal ink. Values, titles, control text at rest, readouts, selected rows. Measured at 13:1 on a plate.
- **Soft Cyan** (`oklch(78% 0.09 200)`): dock readouts and volume value, and the de-escalated Remove key in queue and layer rows. Measured at 9.5:1 on a plate.
- **Dim Cyan** (`oklch(68% 0.06 205)`): data labels, row metadata, status strip text, empty-state readouts, link state at rest. Measured at 6.5:1 on a plate.
- **Faint Cyan** (`oklch(63% 0.045 210)`): placeholders and the uploader/duration meta on rows. Measured at 5.4:1 on a plate.

### Secondary
- **Sodium Lamp** (`oklch(82% 0.15 68)`): the live-or-locked lamp. The blinking title lamp, the tuning needle edge and head, the volume thumb, the playing corner lamp, the connected link state, focus outlines, hover ink, toast edge, and the 2px top seams on overlay surfaces. Legend plates and status chips stamp a cyan dot instead. Clears 4.5:1 on every plate it sits on (5.8:1 on the dock rail).
- **Dim Sodium** (`oklch(60% 0.11 60)`): the paused lamp, hover borders, the needle at pause. Measured at 4.5:1 on a plate.

### Tertiary
- **Signal Red** (`oklch(70% 0.18 25)`): errors and destruction only: error boxes, the offline chip, danger key ink, the stale badge, the bot-offline warning, search error text, the reconnecting link state. Measured at 6.4:1 on a plate.
- **Deep Signal Red** (`oklch(44% 0.1 25)`): borders of alert elements and the danger key at rest.

### Neutral
- **Cold Graphite** (`oklch(14% 0.012 250)`): page ground and the sunk wells (inputs and the tuning strip darken it further toward black).
- **Steel Plate** (`oklch(19% 0.016 250)`): panel interiors and disabled key backgrounds.
- **Raised Steel** (`oklch(24% 0.022 250)`): keys, action strips, popovers, search dropdown, toasts.
- **Signal Rail** (`oklch(37% 0.07 250)`): the two fixed rails, the header and the transport dock.
- **Deep Rail** (`oklch(28% 0.05 250)`): legend plates, status strip, status chips, dock keys.
- **Hairline** (`oklch(38% 0.03 250)`): default 1px border, row separators, gauge tracks.
- **Bright Hairline** (`oklch(56% 0.05 250)`): rail borders, plate borders, chip borders, scrollbar thumb, toasts.
- **Major Tick** (`oklch(56% 0.05 250 / 0.72)`), **Minor Tick** (`oklch(56% 0.05 250 / 0.34)`), **Seam** (`oklch(56% 0.05 250 / 0.4)`): three alpha steps of Bright Hairline. Major ticks rule at full height every 2rem, minor ticks at roughly half height every 0.5rem, and the seam inks the bottom edge of the header rail and dock. In the stylesheet they are `color-mix(in oklab, var(--line-strong) N%, transparent)`.
- **Idle Gray** (`oklch(50% 0.02 250)`): disabled control ink only, measured at 3.1:1. Its low contrast is intentional and it must not leak into readable content.

### Named Rules
**The Red Means Broken Rule.** Red marks only errors, alerts, and destruction. There is no green: OK state is the cyan signal ink, live state is sodium, broken state is red. The design-language test enforces both halves (no green anywhere; red literals only on lines that say alert).

**The Locked Lamp Rule.** Sodium is the dial lamp, not a paint. It appears on the needle, the playing corner lamp, the title lamp, focus rings, the connected link, and hover ink. Never as body copy and never as a resting fill.

## Typography

**Display Font:** Michroma (with Chivo Mono and ui-monospace fallbacks)
**Body Font:** Chivo Mono (with ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, Liberation Mono fallbacks)

**Character:** One weight, two voices. Michroma, the squared techno face, is the legend voice: plates, band headings, keys, chips, the wordmark, and the track title. Chivo Mono is the instrument readout voice: values, data labels, metadata, inputs. There is no weight contrast anywhere in the build (every declared weight is 400), so hierarchy comes from family, size, tracking, and case alone. The smallest step anywhere is 0.7rem (about 11.2px).

### Hierarchy
- **Display** (400, 1.05rem, tracking 0.18em): the page title (Music), trailed by a 0.45rem blinking sodium lamp; the track title takes the same size at 0.05em tracking.
- **Title** (400, 0.85rem, tracking 0.3em): the HARPI wordmark on its plate.
- **Band** (400, 0.8rem, tracking 0.2em): the Music, System, and Layers headings, each trailed by a 1px rule that fills the remaining width.
- **Legend** (400, 0.7rem, tracking 0.22em, uppercase): panel legend plates (NOW PLAYING, QUEUE, LAYERS, SESSION, SEARCH, ACCESS).
- **Control** (400, 0.7rem, tracking 0.16em, uppercase): keys, status chips, link state.
- **Body** (400, 1rem, line-height 1.5): Chivo Mono default, sentence case.
- **Value** (400, 0.8rem): data rows, readouts, input text (0.78rem), select text (0.78rem), tabular numerals wherever a number can change.
- **Label** (400, 0.7rem, tracking 0.14em, uppercase): data keys, row metadata, toasts, status strip.

### Named Rules
**The Two-Family Rule.** Michroma and Chivo Mono, nothing else. Stacks may carry only the two faces and their listed fallbacks. The design-language test checks every font stack and both `--font-*` tokens.

**The Legends and Values Rule.** Legends and controls set in Michroma, uppercase with wide tracking. Everything the machine reports (data labels, values, metadata, inputs) sets in Chivo Mono. No digit is ever set in Michroma; no legend plate is ever set in mono.

## Layout

Single column capped at 72rem and centred. The app shell pads 0.5rem top, 1.25rem sides, and reserves the fixed chrome at the bottom with `calc(1.75rem + var(--transport-height) + 1rem)`. Blocks in the main column stack with 1rem gaps; panels pad 1rem; a legend plate sits 0.85rem above panel content.

The Music band is the only split layout: at 56rem and up, a two-column grid pairs a fluid main column (Now Playing over Queue) with a fixed 20rem Layers rail; below it, one column, and the rail collapses with a Hide key and reopens with a Show key. The Session readouts grid auto-fits at `minmax(11rem, 1fr)`; the Now Playing readouts at `minmax(7rem, 1fr)` (2 columns under 30rem); the queue list caps at 40vh and scrolls.

Fixed chrome stacks from the bottom: the status strip at the very bottom (a rail-deep band with a 1px top hairline), the transport dock 1.75rem above the viewport bottom, toasts just above the dock's right corner, the error region mirrored on the left. Everything that must clear the dock reads `calc(1.75rem + var(--transport-height) + 0.5rem)` (the shell reserves 1rem), so a wrapped dock on a phone never covers content.

Breakpoints (observed): 30rem collapses the header to wrapped rows, hides the shortcut hint, wraps queue and search rows, hides the readout title, drops the dock readout's time when offline while the warning plate stays, and drops the tuning strip to a full-width row; 48rem caps the dock readout at 22ch; 56rem enables the Music split. The design language never switches off at any width: density collapses, identity stays.

Spacing rhythm: 0.35rem inside rows, 0.5rem between related controls, 0.75rem inside clusters, 0.85rem from a legend plate to its content, 1rem between panels, 1.25rem page gutters.

### Named Rules
**The Measured Dock Rule.** The transport dock measures its own height with a ResizeObserver and publishes it as `--transport-height` (2.85rem before the first measure). Fixed chrome and the shell clear the dock through that variable; a hardcoded dock height is a bug.

## Elevation & Depth

The system is flat, tonal, and seam-stitched. There are no drop shadows anywhere; the only `box-shadow` in the stylesheet is an inset 1px sodium underline on the active search row. Depth comes from five moves: the tonal ladder (ground, plate, plate-2, rail-deep, rail); 1px hairlines in `line` and `line-strong`; 2px plate seams (bottom edges of raised plates and keys in a darkened hairline, top edges of overlay surfaces in sodium); sunk wells (inputs and the tuning strip sit in ground darkened 85% and 82% toward black); and dimmed backdrops (ground 55% black behind the confirm dialog, black 60% behind the search palette).

### Shadow Vocabulary
- **Active row underline** (`box-shadow: inset 0 -1px 0 var(--lamp)`): marks the active search result row. The only shadow in the system.

### Named Rules
**The Seam Rule.** Raised plates take a 2px seam on their bottom edge; overlays take a 2px sodium seam on their top edge. Seams are the only 2px lines in the system; every other edge is a 1px hairline.

**The Flat Rule.** No drop shadows, no glows, no decorative gradients. The only gradients are the tube layer's scanlines and vignette and the ruled tick scales. If a surface needs separation, give it a tonal step, a hairline, or a seam.

## Motion

Motion explains the receiver; it never decorates. Three behaviors and one vocabulary:

- **Lock-on (the focal moment).** When the panel locks a signal (first play, resume, or a new track while playing) the Now Playing calibration edge lights sodium once, left to right, in 620ms of deceleration, and the corner lamp steps on through a double blink before holding. It runs once per lock, never on progress ticks. Nothing else in the panel celebrates.
- **Arrival.** Queue, layer, and search rows arrive as log lines: a fade with 0.3rem of travel over `--motion-settle` (220ms), staggered 25–30ms per row and capped at six rows, so a list appears as a list. Dialogs drop 0.5rem, popovers and select lists wipe open top-down (a clip-path reveal), toasts slide in from the right corner, fault plates from the left. Gauges sweep from zero once on arrival. List rows use FLIP (200ms) so removal slides the survivors instead of snapping them.
- **Settle.** The tuning strip's fill eases between progress updates (180ms ease-out), so the needle drifts rather than jumps; it snaps while the operator drags (`.is-seeking`), because direct manipulation is instant. That fill is the one width the system animates: it is a single absolutely positioned element, so the layout cost stays bounded to it, and a transform would distort the 1px edge and the needle sitting on it. Hover, focus, disabled, link, and chip color changes settle in `--motion-quick` (140ms). The playing lamp dims to paused over 220ms.

The only repeating motion is the two step blinks (title lamp, offline lamp, boot mark), each behind `prefers-reduced-motion: no-preference`. There are no spinners, skeletons, or progress theatrics; waiting is text in place.

Timing lives in three tokens: `--motion-quick` (140ms, state color), `--motion-settle` (220ms, arrivals), `--ease-arrive` (`cubic-bezier(0.16, 1, 0.3, 1)`, a confident deceleration). One-shot signatures may exceed them; the lock wipe runs 620ms.

Under `prefers-reduced-motion: reduce` every arrival, wipe, sweep, and blink is removed and the element renders in its final state. The 140ms color settles stay: they carry state, not movement. The lock wipe is hidden entirely.

### Named Rules
**The One Celebration Rule.** The lock-on wipe is the only authored moment. Everything else is arrival, settle, or a gated blink.

## Shapes

Zero radius. Every corner in the system is square (the only `border-radius` declaration in the stylesheet is `0`, on the Firefox range thumb). There are no circles anywhere: every lamp, dot, and indicator is a square. The form vocabulary is squares and thin rectangles: 0.35rem dots (cyan on legend plates and chips), the 0.45rem title lamp, the 0.7rem playing corner lamp, the 4px by full-height slider thumb, the 0.7rem by 0.35rem needle head, 0.3rem gauge bars, and the "01"-style index digits as row markers. The select chevron is a 0.4rem square rotated 45 degrees with two 1px borders. Borders come in exactly two widths: 1px hairlines and 2px seams.

### Named Rules
**The Zero Radius Rule.** Every corner is square and every border is a hairline or a seam. No rounded corners, no pills, no circles, no clip paths.

## Components

The panel's controls are instrument keys and legend plates: flat plates with hairline edges and a 2px bottom seam, uppercase Michroma legends, and state carried by lit squares. Hover lights a control's ink and borders in sodium; it never floods a control with a solid fill.

### Keys (Buttons)
- **Shape:** square, 1px `line` border, 2px bottom seam in `line` darkened 55% toward black, min-width 4.5rem, padding 0.5rem 1.05rem 0.45rem.
- **Primary:** raised-steel background, Phosphor Cyan ink, Michroma 0.7rem tracking 0.16em uppercase, line-height 1.
- **Hover / Focus:** hover lifts ink and borders to sodium (lamp ink, lamp-dim border, lamp bottom seam). Active translates the key down 1px. Focus-visible draws a 1px sodium outline at 2px offset; forced-colors swaps in a 2px Highlight outline. Disabled keys drop to Idle Gray on a plate background with a not-allowed cursor. While an action is in flight the key disables and its label changes (Checking…, Reconnecting…): per-action feedback, no skeletons.
- **Danger:** Signal Red ink on alert-dim borders at rest; hover floods alert 16% into the raised steel and brightens the borders to full alert. In queue and layer rows the Remove key de-escalates to Soft Cyan with hairline borders until hovered: destruction stays quiet until it is aimed at.
- **Action strip:** the panel's bottom edge. Full-bleed (negative margins to the panel edges), raised-steel background, 1px top hairline, 1px dividers between keys, right-aligned. Hover tints sodium 10% (danger 14% red). Dialog strips keep the same plate. On coarse pointers keys and inputs rise to a 2.75rem minimum height.

### Chips
- **Status chip:** rail-deep plate, 1px `line-strong` border, Michroma 0.7rem tracking 0.16em, a 0.35rem square lamp. Online reads ONLINE with a cyan lamp; offline reads OFFLINE in Signal Red with an alert-dim border and a red lamp blinking at 1s steps(2). This is the only blinking chip, and it blinks only for a broken carrier.
- **Link state:** Michroma 0.7rem tracking 0.16em. LINK LIVE in sodium, LINK LOST in red, LINKING in dim cyan.

### Cards / Containers
- **Panel:** the one container. Steel-plate interior, 1px `line` border, 1rem padding, and a ruled calibration scale pinned across its top edge (0.35rem tall; major ticks 1px every 2rem at full height, minor ticks every 0.5rem at 45% height).
- **Legend plate:** the panel title, and the only place a panel gets one. Deep-rail plate, 1px `line-strong` border, 2px bottom seam, a 0.35rem sodium dot, Michroma 0.7rem tracking 0.22em uppercase.
- **Playing lamp:** a panel in play grows a 0.7rem sodium square capping its top-left corner; it steps on with the lock (a double blink, then steady) and dims to paused over 220ms. Only the Now Playing panel carries it.
- **Action strip:** see Keys.

### Inputs / Fields
- **Style:** the sunk well: ground darkened 85% toward black, 1px `line` border, Phosphor Cyan text at 0.78rem, padding 0.45rem 0.65rem, square.
- **Focus:** a 1px sodium outline at 2px offset. The volume controls take the same outline at 3px offset via `:focus-within`.
- **Placeholder:** Faint Cyan. The search field's clear control is drawn from two 1px bars in dim cyan, lifting to sodium on hover; the native webkit cancel button is hidden because it renders in the OS's own colors.
- **Select:** the panel never renders a native select popup. The trigger is a key-like plate (raised steel, hairline, 2px bottom seam, 0.78rem text) with a 0.4rem rotated-square chevron that sits over a listbox: raised-steel overlay, `line-strong` hairline, 2px sodium top seam, options separated by hairlines, the active option tinted cyan 10%. Full keyboard model: arrows, Home/End, Enter/Space, Escape, 500ms typeahead, outside-click close.
- **Search palette:** a modal dialog capped at 42rem, 12vh from the top, on a black 60% backdrop. Legend plate "Search", the field over a raised-steel results list; the active row tints cyan 10% over a 1px sodium inset underline. A strip below names the selected track beside the Queue and Layer keys. Waiting states are text in place (Searching…), errors are red status lines.

### Navigation
- There is no nav: the panel is a single surface. The header rail is the wayfinding: a wordmark plate (deep-rail plate, 2px bottom seam, the pixel mark at 2rem beside HARPI in Michroma 0.85rem tracking 0.3em), the output readout, and the search key with its shortcut hint (Ctrl K, or the command key on a Mac; hidden under 30rem).
- **Output readout:** a deep-rail trigger plate holding the OUTPUT data label, the guild and channel value, the status chip, and the link state. Its popover is a raised-steel overlay with a 2px sodium top seam holding the Guild and Channel selects and the Connect/Disconnect keys. Under 30rem the rail wraps and the readout takes a full row.

### The Tuning Strip (signature)
- The seek control is a calibrated frequency rail in the dock: flex 1, min-width 8rem, height 1.9rem (2.75rem on coarse pointers), sunk in ground 82% toward black, ruled with major ticks every 2rem at full height and minor ticks every 0.5rem at 42%, inside a 1px border of ink at 22%.
- **Fill and needle:** the tuned span sits at ink 18% with a 1px sodium right edge, and the needle head is a 0.7rem by 0.35rem sodium rectangle overhanging the edge by 0.35rem. The track grabs on pointer down (grab/grabbing cursors, touch-action none) and seeks to the drop point.
- **Paused:** the fill drops to ink 6% and both the edge and the needle head dim to dim sodium.
- **Offline:** `aria-disabled`, a not-allowed cursor, and every seek gesture and key is gated. The dock readout prepends a red "Bot offline" warning chip to the position, and under 30rem the whole readout hides.
- **Keyboard:** `role="slider"` with aria-valuemin/max/now; arrows seek 5s, PageUp/PageDown 15s, Home/End jump to the ends; focus takes the 1px sodium outline. Under 30rem the strip wraps to a full-width row beneath the keys.
- **The dock around it:** signal-rail background, 1px `line-strong` top border with a seam-colored bottom edge, a 0.2rem tick scale riding above its top border, keys seated in deep rail with `line-strong`-at-70% borders, and 1px dividers (ink 18%) between all children.

### Readouts and Gauges
- **Readout cell:** a data label (Chivo Mono 0.7rem tracking 0.14em uppercase, dim cyan) over a value (Chivo Mono, Phosphor Cyan, tabular numerals), separated by a 1px top hairline.
- **Queue gauge:** a 4rem by 0.3rem bar per queue row, filled in dim cyan proportional to the longest queued track over a track of hairline at 80% ink. A readout, not a control.
- **Queue row:** index in dim cyan, 32px thumbnail, title, gauge, "uploader · duration" in faint cyan, Remove key.
- **Empty states:** uppercase dim-cyan readouts ("Queue empty — search to add tracks.", "No layers — add one from Search.") beside the key that fixes it (Search), or a lone empty line when there is no session.
- **Stale badge:** "bot offline" in a red hairline box inside the Now Playing legend plate.

### Toasts and Errors
- **Toast:** a fixed column above the dock's right corner: raised steel, 1px `line-strong` border with a 1px sodium left edge, uppercase Chivo Mono 0.7rem. Confirmations only; errors never arrive here. Undo actions (Re-add) ride inside the toast as a key.
- **Error region:** fixed above the dock's left corner: persistent red boxes (Signal Red text on alert mixed 8% into a plate, 1px alert border) with Dismiss and, for contract violations, Refresh keys.
- Both clear the dock through `calc(1.75rem + var(--transport-height) + 0.5rem)`.

### Browser Surfaces and the Tube
- **Selection:** Phosphor Cyan background, ground text. **Caret:** sodium. **Scrollbars:** thin, `line-strong` thumb on a transparent track (webkit: 10px wide, 3px ground border).
- **Tube layer:** one fixed pseudo-element over the whole viewport (z-index 50, pointer-events none): 1px scanlines at 9% black every 4px plus a vignette fading to 24% black at the edges. No flicker, no curvature. Toasts and errors sit above it; the dock, strip, and panels below it.
- **Boot and sign-in:** the boot screen shows the pixel mark beside "Linking…" in Michroma dim cyan; the sign-in panel is a legend-plated panel ("Access") with the HARPI PANEL title, a token field, and a full-width ENTER key.

## Do's and Don'ts

### Do:
- **Do** keep every corner square (0px radius) and every edge a 1px hairline; the only 2px lines are plate seams (bottom on raised plates and keys, sodium top on overlays).
- **Do** ink readings in the cyan ladder and light sodium only for what is live or locked: needle, playing corner lamp, title lamp, focus ring, connected link, hover.
- **Do** draw the ruled scales wherever a surface needs texture: major ticks 1px every 2rem, minor ticks 1px every 0.5rem, in the two tick inks.
- **Do** seat every panel title in a legend plate with its 0.35rem sodium dot and 2px bottom seam.
- **Do** set legends and controls in Michroma, data in Chivo Mono, and keep the smallest type at the 0.7rem floor.
- **Do** uppercase and track everything that labels (0.14em to 0.3em).
- **Do** keep depth tonal: ground, plate, plate-2, rail-deep, rail, hairlines, seams.
- **Do** theme the browser surfaces: ink-on-ground selection, sodium caret, hairline scrollbars.
- **Do** gate every blink, arrival, wipe, and sweep behind `prefers-reduced-motion: no-preference`; keep the 140ms color settles under it, because they carry state rather than movement (see Motion).
- **Do** let the fixed chrome clear the dock through `--transport-height`.
- **Do** keep destructive keys quiet (Soft Cyan, hairline borders) until they are hovered in list rows.

### Don't:
- **Don't** introduce green anywhere: OK is the cyan signal ink, live is sodium, broken is red. The design-language test fails on any green.
- **Don't** use red outside alerts and destruction; a red literal is only legal on a line that says alert.
- **Don't** add a third font family; stacks carry only Michroma, Chivo Mono, and their listed fallbacks.
- **Don't** invert keys to a solid fill on hover; hover lights the ink and borders instead.
- **Don't** paint sodium as body copy or as a resting surface fill.
- **Don't** add drop shadows or glows; the only box-shadow is the active-row inset underline.
- **Don't** round a corner, add a pill, or draw a circle.
- **Don't** add spinners, skeletons, or fake progress: waiting is text in place (Linking…, Checking…, Reconnecting…, Searching…). Motion is arrivals, settles, blinks, and the one lock wipe: no loops on content, no bounce or elastic curves, no scroll effects, no movement on numbers.
- **Don't** use thick borders beyond the 2px seams.
- **Don't** let Idle Gray leak into readable content.
- **Don't** ship the OS-native select popup or the native search-cancel button; overlays are built in-world.
