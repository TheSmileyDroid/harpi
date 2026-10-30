---
name: Harpi
description: A posted placard board for a working guild, where every state is a placard pairing a claim with the value that proves it.
colors:
  ground: "#14110d"
  plate: "#1f1b15"
  plate-2: "#2a241c"
  sunken: "#0d0b08"
  rating: "#191510"
  rule: "#2a241c"
  rule-strong: "#3d3527"
  sand: "#e9dfc7"
  on-sand: "#221e18"
  amber: "#f2b24e"
  label: "#c4b79d"
  dim: "#a59a8a"
  faint: "#948a79"
  oxide: "#ce7442"
  alert: "#f0604a"
  alert-well: "#2a1712"
  alert-ink: "#d9c7b4"
  idle: "#7d7365"
typography:
  display:
    fontFamily: "Urbanist, system-ui, sans-serif"
    fontSize: "0.95rem"
    fontWeight: 800
    lineHeight: 1
    letterSpacing: "0.16em"
  headline:
    fontFamily: "Urbanist, system-ui, sans-serif"
    fontSize: "1.375rem"
    fontWeight: 700
    lineHeight: 1.15
    letterSpacing: "-0.01em"
  plate:
    fontFamily: "Urbanist, system-ui, sans-serif"
    fontSize: "0.75rem"
    fontWeight: 700
    lineHeight: 1
    letterSpacing: "0.18em"
  placard:
    fontFamily: "Barlow, system-ui, sans-serif"
    fontSize: "0.6875rem"
    fontWeight: 600
    lineHeight: 1
    letterSpacing: "0.16em"
  stamp:
    fontFamily: "Urbanist, system-ui, sans-serif"
    fontSize: "0.8125rem"
    fontWeight: 800
    lineHeight: 1
    letterSpacing: "0.14em"
  control:
    fontFamily: "Barlow, system-ui, sans-serif"
    fontSize: "0.72rem"
    fontWeight: 600
    lineHeight: 1
    letterSpacing: "0.14em"
  label:
    fontFamily: "Barlow, system-ui, sans-serif"
    fontSize: "0.6875rem"
    fontWeight: 600
    lineHeight: 1.5
    letterSpacing: "0.12em"
  value:
    fontFamily: "JetBrains Mono, ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, Liberation Mono, monospace"
    fontSize: "0.8125rem"
    fontWeight: 400
    lineHeight: 1.5
    letterSpacing: "normal"
  meta:
    fontFamily: "JetBrains Mono, ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, Liberation Mono, monospace"
    fontSize: "0.75rem"
    fontWeight: 400
    lineHeight: 1
    letterSpacing: "0.02em"
rounded:
  key: "3px"
  plate: "4px"
spacing:
  xs: "0.35rem"
  sm: "0.5rem"
  md: "0.75rem"
  lg: "0.85rem"
  xl: "1rem"
  gutter: "1.25rem"
components:
  placard:
    backgroundColor: "{colors.plate-2}"
    textColor: "{colors.sand}"
    typography: "{typography.placard}"
    rounded: "{rounded.key}"
    padding: "0.4rem 0.6rem"
    height: "2.5rem"
  placard-flipped:
    backgroundColor: "{colors.sand}"
    textColor: "{colors.on-sand}"
    typography: "{typography.placard}"
    rounded: "{rounded.key}"
    padding: "0.4rem 0.6rem"
    height: "2.5rem"
  key:
    backgroundColor: "transparent"
    textColor: "{colors.label}"
    typography: "{typography.control}"
    rounded: "{rounded.key}"
    padding: "0.65rem 0.8rem"
    height: "2.5rem"
    width: "3.5rem"
  key-hover:
    backgroundColor: "{colors.plate-2}"
    textColor: "{colors.sand}"
  key-primary:
    backgroundColor: "{colors.sand}"
    textColor: "{colors.on-sand}"
    typography: "{typography.control}"
    rounded: "{rounded.key}"
    padding: "0.65rem 0.8rem"
    height: "2.5rem"
  key-primary-hover:
    backgroundColor: "color-mix(in srgb, {colors.sand} 76%, white)"
  key-disabled:
    backgroundColor: "transparent"
    textColor: "{colors.idle}"
  key-danger-hover:
    backgroundColor: "{colors.alert-well}"
    textColor: "{colors.alert}"
  panel:
    backgroundColor: "{colors.plate}"
    rounded: "{rounded.plate}"
    padding: "1rem"
  rating-cell:
    backgroundColor: "{colors.rating}"
    typography: "{typography.value}"
    padding: "0.5rem 0.6rem"
  input:
    backgroundColor: "{colors.sunken}"
    textColor: "{colors.sand}"
    typography: "{typography.value}"
    rounded: "{rounded.key}"
    padding: "0.55rem 0.7rem"
  select-trigger:
    backgroundColor: "{colors.plate-2}"
    textColor: "{colors.sand}"
    typography: "{typography.value}"
    rounded: "{rounded.key}"
    padding: "0.5rem 0.6rem"
  toast:
    backgroundColor: "{colors.plate-2}"
    textColor: "{colors.sand}"
    typography: "{typography.label}"
    rounded: "{rounded.key}"
    padding: "0.5rem 0.7rem"
  panel-label:
    textColor: "{colors.sand}"
    typography: "{typography.plate}"
  state-stamp:
    textColor: "{colors.amber}"
    typography: "{typography.stamp}"
  seek-track:
    backgroundColor: "{colors.sunken}"
    rounded: "{rounded.key}"
    height: "2.5rem"
  action-strip:
    backgroundColor: "{colors.plate-2}"
    rounded: "{rounded.plate}"
    padding: "0.7rem 0.7rem"
  fault-plate:
    backgroundColor: "{colors.alert-well}"
    textColor: "{colors.alert-ink}"
    rounded: "{rounded.plate}"
    padding: "0.8rem 0.7rem 0.7rem 0.9rem"
---

# Design System: Harpi

## Overview

**Creative North Star: "The Posted Placard"**

The world is **HAZARD PLACARD**. The panel is a posted placard board for a working guild, not a dashboard. Every state is a placard: a claim set in Barlow small caps paired with the value that proves it set in JetBrains Mono, both pressed into a plate-toned tag. The board is a warm near-black ground (`#14110d`) carrying plate tones (`#1f1b15`, `#2a241c`). Sand (`#e9dfc7`) is the material of what the operator presses: the primary key, the search sheet's Queue key, the sign-in key, and the carrier placard. Amber (`#f2b24e`) marks state and every live reading: placard legends, the state stamp, the seek scale and its fill, the volume value. Oxide (`#ce7442`) is the caution ink: hover borders and the paused seek fill. Hazard red (`#f0604a`) means breakage: the stale badge, the offline chip and lamp, the fault plate, and the banded hazard strip.

It refuses the category-default card grid. Placards pack to their edges and divide with 1px rules instead of gaps. The rating plate packs four readouts into one bordered bed. The transport is an equipment rating plate you press: a stepped amber seek scale, a ruled volume scale, keys, and a readout, all in one fixed dock. Banded hazard appears in exactly two places, the carrier placard when it flips and a fault plate.

Materials carry the identity. Urbanist sets headings and the two stamps, Barlow sets legends, controls and labels, JetBrains Mono sets values. Corners are 3px on keys and placards, 4px on plates and bars, 1px on instrument bits. Sand surfaces carry printed grain and a printed edge. Nothing glows and no text is gradient-filled. Depth is a tonal ladder plus 1px rules, with one drop shadow in the whole system.

Motion is one authored moment and nothing else. When the carrier drops, the carrier placard inverts to sand under a 0.4rem banded hazard strip and every transport key strikes out. Everything else is arrival (rows, dialogs, overlays), settle (color changes, the seek fill), or a gated blink (the offline lamp, the boot mark). The panel was built at 1440x900 and 390x844: the smallest rendered type is 11px at both widths, and at maximum scroll the lowest panel clears the dock by 24px at both.

The binding commitment from PRODUCT.md holds: the panel's retrofuturist industrial-placard identity is Harpi's visual direction, it replaced the unmarked-carrier receiver world, and future work extends it.

**Key Characteristics:**
- Placards, not cards: every state is a claim plus the value that proves it
- Sand is the pressed material, amber is the state lamp, hazard banding means breakage
- Warm near-black board (`#14110d`) under plate tones (`#1f1b15`, `#2a241c`)
- Three faces with one job each: Urbanist headings and stamps, Barlow legends and labels, JetBrains Mono values
- 3px key corners, 4px plate corners, 1px rules, square lamps
- One authored moment (the placard flip), with everything else arriving, settling, or blinking behind a motion preference

### Named Rules
**The One Moment Rule.** The placard flip is the only authored moment. Arrival, settle, and gated blinks are the entire rest of the motion vocabulary.

## Colors

A warm near-black board carrying plate-toned placards, inked in amber for state and bone for reading, with oxide and hazard red held back for caution and breakage.

### Primary
- **State Amber** (`#f2b24e`): the state lamp and the live reading. Placard legends, the Now Playing state stamp, the seek scale and its fill, the volume value, queue and layer indices, the reconnect point for hover on plates. Measured at 9.2:1 on a plate and 8.2:1 on a raised plate.
- **Placard Sand** (`#e9dfc7`): the material of what the operator presses, and the ink of titles. The primary key, the search sheet's Queue key, the flipped carrier placard, the sign-in key, plus track titles, band names and readout values. Measured at 12.9:1 on a plate.

### Secondary
- **Oxide Caution** (`#ce7442`): the caution band and the hover border. Hover borders on keys and select triggers, and the seek fill while paused. Measured at 5.1:1 on a plate.

### Tertiary
- **Hazard Red** (`#f0604a`): breakage only. The offline carrier chip and lamp, the stale badge on the Now Playing band, the stale tag in the top bar, the Hazard stamp, fault-plate borders, the bot-offline chip, the reconnecting link state, search failure text, and the light stripes of the hazard band. Measured at 5.3:1 on a plate.
- **Hazard Well** (`#2a1712`): the bed under hazard plates and the dark stripe of the hazard band.
- **Hazard Ink** (`#d9c7b4`): the readable ink on the hazard well. Measured at 10.4:1 on the well.

### Neutral
- **Warm Near-Black** (`#14110d`): the page ground, and the base of the dimmed modal backdrops.
- **Placard Plate** (`#1f1b15`): panel interiors, the placard bar, and the disabled primary key's fill.
- **Raised Plate** (`#2a241c`): placards, action strips, toasts, popovers, the search results list, the transport dock. The separator ink (`rule`) is this same value, so a 1px row rule reads as a plate tone rather than a line.
- **Sunken Well** (`#0d0b08`): inputs and the two scales (the seek track, the volume slider) sit below the ground.
- **Rating Bed** (`#191510`): the readout grid inside a rating plate, one step under a panel.
- **Bright Rule** (`#3d3527`): the 1px border on plates, placards, keys, inputs, thumbnails and the scrollbar thumb.
- **Bone Label** (`#c4b79d`): body text and key ink at rest. Measured at 9.5:1 on the ground.
- **Dim Ash** (`#a59a8a`): data labels, row metadata, the status strip, the boot plate, the readout title. Measured at 6.2:1 on a plate.
- **Faint Ash** (`#948a79`): placeholders, uploader and duration meta, panel meta. Measured at 5.0:1 on a plate.
- **Sand Ink** (`#221e18`): the ink printed on sand, used by the flipped placard and the primary key. Measured at 12.5:1 on placard sand.
- **Struck Gray** (`#7d7365`): disabled ink only, measured at 3.7:1. Its low contrast is intentional and it must not leak into readable content.

### Named Rules
**The One Lamp Rule.** Amber is the state lamp, not a paint. It appears on legends, the state stamp, live readings, the seek scale, the volume value and hover ink. Never as body copy and never as a resting surface fill.

**The Hazard Means Break Rule.** Banded hazard appears only when the carrier drops and on a fault plate. A healthy surface never carries a hazard strip, and oxide stays a caution band and a hover border.

**The Sand Is What You Press Rule.** Sand is the material of the pressed surface. Only the primary key, the search sheet's Queue key, the flipped carrier placard and the sign-in key are sand, and each carries the printed grain and a printed edge.

## Typography

**Display Font:** Urbanist (with system-ui, sans-serif)
**Label Font:** Barlow (with system-ui, sans-serif)
**Value Font:** JetBrains Mono (with ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, Liberation Mono, monospace)

**Character:** Three faces with one job each. Urbanist is the heading voice: the wordmark, the page title, panel bands, the track title, dialog titles and the two stamps. Barlow is the legend voice: placard labels, data labels, keys, chips, link state, toasts and every prose line. JetBrains Mono is the value voice: values, metadata, inputs, indices, the status strip. Hierarchy comes from family, size, tracking and case, never from a synthetic width axis. Weights are 800 for the display title and the stamps, 700 for plate labels and the track title, 600 for placard, control and label, 500 for track names, 400 for values and metadata. The smallest step anywhere is 0.6875rem (11px, measured at both widths).

### Hierarchy
- **Display** (800, 0.95rem, tracking 0.16em, uppercase): the page title and the boot plate. The wordmark narrows it to 0.85rem at 0.24em, and the sign-in title widens it to 1rem.
- **Headline** (700, 1.375rem, line-height 1.15, tracking -0.01em): the track title in the Now Playing plate, dropping to 1.125rem and wrapping under 30rem.
- **Plate** (700, 0.75rem, line-height 1, tracking 0.18em, uppercase): the panel label, trailed by a 1px rule that fills the remaining width.
- **Placard** (600, 0.6875rem, line-height 1, tracking 0.16em, uppercase): placard labels, the link state, the carrier chip.
- **Stamp** (800, 0.8125rem, line-height 1, tracking 0.14em, uppercase): the state stamp and the Hazard stamp. The state stamp is always amber, whatever the carrier is doing: it reports playback, and the carrier's health is the stale badge's job. The Hazard stamp is hazard red.
- **Control** (600, 0.72rem, line-height 1, tracking 0.14em, uppercase): every key.
- **Label** (600, 0.6875rem, tracking 0.12em, uppercase): data labels over their values. Track names in the queue, layer and search rows step up to 0.875rem at weight 500.
- **Value** (400, 0.8125rem, line-height 1.5): the body default, data values, input text. Rating cells step up to 0.9375rem and compact readouts tighten to 1.2. Tabular numerals wherever a number can change.
- **Meta** (400, 0.75rem): system notes, row metadata, the volume value, panel meta, the boot plate's fallback.

### Named Rules
**The Three Faces Rule.** Urbanist for headings and the two stamps, Barlow for legends, controls and prose, JetBrains Mono for values. Nothing else. No value is ever set in Urbanist, and no heading is ever set in JetBrains Mono.

**The Stamp Rule.** Urbanist appears twice as a stamp: the Now Playing state stamp (PLAYING, PAUSED, STOPPED) and the Hazard stamp on a fault plate, both at weight 800 with 0.14em tracking. It is a stamp, not a heading face.

## Layout

The music page is a single column capped at 72rem and centred, padded 0.75rem at the top, 1.25rem at the sides and `calc(var(--transport-height) + 1.5rem)` at the bottom so the fixed dock never sits over content. The placard bar wraps at the top with 0.5rem gaps and 0.5rem padding. Panels stack with 1rem gaps and pad 1rem, and a panel band sits 0.85rem above its content.

The campaign shell is a fixed 14rem rail beside a fluid content column. The content column caps at 72rem, pads 0.75rem at the top and 1.25rem at the sides, and clears its own bottom with 2rem; no dock takes part. Below 56rem the rail becomes a band across the top and the content column starts under it. Panels inside the shell follow the same 1rem stack and 1rem padding as the music page.

The console is one column until 56rem, where it splits into a fluid main column (Now Playing over Queue) and a 15.5rem rail (Layers, Session, Linked). The rail collapses behind a Hide layers key and reopens with Show layers. The rating grid auto-fits at `minmax(7rem, 1fr)`, so four readouts sit in one row on desktop and wrap to two columns on a phone. The queue list caps at 60vh and scrolls until 56rem, where it takes the height left over so the plates meet the dock.

Fixed chrome stacks above the dock: toasts at the right corner (z-index 60), the error region mirrored at the left (65), the output popover below both (40) and a select list under that (50), with the dock itself at 10. Toasts and errors both clear the dock through `calc(var(--transport-height) + 0.5rem)`. Measured on the built panel at maximum scroll, the lowest panel bottom sits 24px above the dock top at both 1440x900 and 390x844. Authored controls clear 40px (keys, inputs and the seek scale at 2.5rem, rising to 2.75rem on coarse pointers) with two exceptions: keys inside a queue or layer row and inside a fault plate sit at 2rem, and the native volume range is 16px tall on desktop.

Breakpoints observed: 30rem is the compact collapse (the placard bar wraps and the output placard takes a full row, the shortcut hint hides, the dock wraps with the keys sharing a row and the readout and status strip hiding, queue and search rows wrap, the seek scale takes a full-width row, the Now Playing art drops to 4rem). At 48rem the dock readout caps at 22ch, and at 56rem the console splits. Coarse pointers raise keys, inputs and select rows to 2.75rem, the dock volume slider to 2.75rem, and the seek scale to 2.75rem. The world never switches off at any width: density collapses, the placards stay.

Spacing rhythm: 0.35rem inside rows, 0.5rem between placards and controls, 0.75rem inside clusters, 0.85rem from a panel band to its content, 1rem between panels, 1.25rem page gutters.

### Named Rules
**The Measured Dock Rule.** The transport bar measures its own height with a ResizeObserver and publishes it as `--transport-height` (2.85rem before the first measure). Fixed chrome and the shell clear the dock through that variable. A hardcoded dock height is a bug.

**The Packed Plate Rule.** Placards and rating cells pack to their edges and divide with hairlines. Gaps separate distinct plates, never cells inside one bed.

## Elevation & Depth

The system is flat, tonal and printed. Depth comes from four moves: a tonal ladder (sunken, rating, ground, plate, raised plate), 1px rules in `rule` and `rule-strong`, printed material (the banded hazard strip, the printed grain, the stepped scales), and dimmed backdrops behind modal surfaces. Exactly one drop shadow exists in the stylesheet, on the output popover. The flipped placard and the primary key take an inset printed edge instead, which reads as the border of a pressed sand surface rather than as elevation.

### Shadow Vocabulary
- **Overlay lift** (`box-shadow: 0 0.75rem 1.6rem rgb(0 0 0 / 0.55)`): the output popover, and the only drop shadow in the system.
- **Printed edge** (`box-shadow: inset 0 0 0 1px color-mix(in srgb, var(--on-sand) 18%, transparent)`): the flipped placard and the primary key, the printed border of a sand surface.
- **Rating dividers** (`box-shadow: inset 1px 0 0 var(--rule), inset 0 -1px 0 var(--rule)`): the rating cells' shared hairlines, so cells need no gaps between them.
- **Dimmed backdrops** (`color-mix(in srgb, var(--ground) 60%, black)` for the confirm dialog, `rgb(0 0 0 / 0.6)` for the search palette): modal separation.

### Named Rules
**The One Shadow Rule.** One drop shadow exists, the output popover's lift. Every other surface separates by a tonal step, a 1px rule, or printed material.

**The Printed Material Rule.** Sand surfaces carry printed grain (a 3px grid of sand ink at 6%) and a printed edge. Hazard surfaces carry the banded strip. Texture is printed, never glowed.

## Shapes

Small radii and thin rules. Keys, placards, inputs, selects, toasts, thumbnails, gauges and the seek track take 3px corners. Panels, the placard bar, action-strip ends, the output popover, dialogs and fault plates take 4px. Instrument bits stay at 1px (the carrier lamp, the gauge bar and its fill) or 2px (the volume thumb, the transport warning chip). There are no pills and no circles: the carrier lamp is a 0.4rem square, the select chevron is a 0.4rem square rotated 45 degrees with two 1px borders, thumbnails are 48px, 32px or 96px squares, the search clear control is two 1px bars crossed, and the seek scale is a stepped strip.

The material vocabulary is striped and printed: the hazard band runs 45 degrees in 8px stripes of hazard red and hazard well, the caution band runs 45 degrees in 5px stripes of oxide, the printed grain is 1px lines on a 3px grid, the seek scale is 7px lit or unlit steps separated by 3px, and the volume scale is a 1px tick every 4px. Borders are 1px everywhere except the 0.4rem hazard strip, which is a printed band rather than a border.

### Named Rules
**The Key and Plate Rule.** Keys, placards, inputs and selects take 3px corners. Panels, bars, popovers, dialogs and fault plates take 4px. Lamps, gauges and thumbs stay at 1px or 2px.

**The Square Lamp Rule.** Every lamp and indicator is a square or a thin rectangle. No circles, no pills, no dots.

## Components

Placards are the state unit, keys are instrument keys, and plates are what holds them. A placard always pairs its claim with a value, a key always lights its ink rather than flooding with a fill, and a sand surface is always the thing the operator presses.

### Placards (the state unit)
- **Shape:** 3px corners, raised-plate fill, min-height 2.5rem, padding 0.4rem 0.6rem, 0.5rem gap between the claim and its value. Hover inside the output trigger lifts the fill to sand at 8% into the raised plate.
- **Claim:** Barlow 600, 0.6875rem, tracking 0.16em, uppercase, amber.
- **Value:** JetBrains Mono 0.8125rem, line-height 1.2, sand, ellipsised. It is never empty: an absent value falls back to a label such as "Select output".
- **The bar:** the placard bar is a raised-plate band with a 1px bright rule, 4px corners, 0.5rem padding and 0.5rem gaps, and it wraps. It holds the wordmark placard, the output placard, the carrier placard, the voice placard, then the Search key and the Sign out key.
- **Flipped:** when the carrier drops, the carrier placard inverts to sand under a 0.4rem banded hazard strip with the printed grain behind it and a printed edge, and both its label and its value switch to sand ink. This is the one place the offline chip is not hazard red: on a sand fill, hazard red measures 2.4:1, so the chip and its lamp take the sand ink and the banded strip carries the hazard.

### Keys (Buttons)
- **Shape:** 3px corners, 1px bright rule, transparent fill, min-height 2.5rem (40px), min-width 3.5rem, padding 0.65rem 0.8rem. Barlow 600, 0.72rem, tracking 0.14em, uppercase, bone ink at rest.
- **Hover / Focus:** hover lifts ink to sand, the fill to the raised plate and the border to oxide. Active translates the key down 1px. Focus-visible draws a 2px amber outline at 2px offset, and forced-colors swaps in a 2px Highlight outline. While an action is in flight the key disables and its label changes (Checking…, Reconnecting…), so waiting is text in place.
- **Primary:** the sand key. A sand fill with the printed grain, dark sand ink on top, a printed border mixed from that ink at 30%, and the inset printed edge. Hover lightens the fill to sand at 76% toward white. Disabled drops the grain and the edge and returns to the placard plate.
- **Danger:** bone ink at rest, so destruction stays quiet. Hover floods the hazard well and brightens the ink and border to hazard red.
- **Disabled (the strike-out):** disabled keys take struck gray ink, a `rule` border, a not-allowed cursor and `text-decoration: line-through`. This is what fires across the transport when the carrier drops.
- **Action strip:** the plate's bottom edge, full-bleed to it with negative margins, raised-plate fill, a 1px `rule` top border, right-aligned keys, and 4px corners matching the plate. Dialog strips keep the same plate.
- **Row keys:** keys inside a queue or layer row and inside a fault plate shrink to a 2rem minimum height with tighter padding. These are the shortest authored targets in the panel (32px).
- **Coarse pointers:** keys and inputs rise to a 2.75rem minimum height.

### Chips (the carrier chip)
- **Carrier:** a 0.4rem square lamp inside the carrier placard beside Barlow 600 at 0.6875rem tracking 0.16em. Online reads ONLINE with an amber lamp in sand text. Offline reads OFFLINE in hazard red with a hazard-red lamp that blinks at 1s `steps(2)`, gated behind a motion preference. On the flipped placard the chip and its lamp take the sand ink instead, because hazard red on sand measures 2.4:1. This is the only blinking chip.
- **Link state:** Barlow 600, 0.6875rem, tracking 0.16em. LINK LIVE in amber, LINK LOST in hazard red, LINKING in dim ash.
- **Stale tag:** a hazard-red tag beside the link state, Urbanist 700 at 0.6875rem tracking 0.16em uppercase, 1px hazard-red border, 2px corners, reading STALE. It appears as soon as the link drops, or when no status, position, or directory frame has arrived for 15 seconds, and clears on the next one. While it is up, readout values, the Now Playing title, and the dock readout drop to 45% opacity; every control stays live.

### Cards / Containers
- **Panel:** the one container. Placard plate interior, 1px bright rule, 4px corners, 1rem padding.
- **Panel band:** a plate label in Urbanist 700 at 0.75rem tracking 0.18em uppercase, sand, trailed by a 1px rule that fills the remaining width, with an optional right-hand meta in JetBrains Mono 0.75rem, faint ash, tabular. The Now Playing band ends with the state stamp, and a hazard-red stale badge ("bot offline") joins it when the carrier is down.
- **Rating plate:** a grid of cells in the rating bed at `minmax(7rem, 1fr)`, divided by inset hairlines rather than gaps, 3px corners, overflow hidden. Each cell pads 0.5rem 0.6rem and holds a data label over a value that steps up to 0.9375rem.
- **Empty state:** an uppercase dim-ash readout beside the key that fixes it (Search), or a lone empty line when there is no session.
- **Thumbnail:** a square at 96px (Now Playing, 4rem under 30rem), 48px (search rows) or 32px (queue and layer rows), with a 1px bright rule and 3px corners. A missing thumbnail draws a 45-degree hatch in the bright rule over the raised plate.

### Inputs / Fields
- **Style:** the sunken well. `#0d0b08` fill, 1px bright rule, 3px corners, sand text at 0.8125rem, padding 0.55rem 0.7rem. Placeholder in faint ash.
- **Focus:** a 2px amber outline at 2px offset. The volume controls take the same outline at 3px offset through `:focus-within`.
- **Select:** the panel never renders a native popup. The trigger is a plate-like control (raised-plate fill, bright rule, 3px corners, 0.8125rem sand) with a 0.4rem rotated-square chevron that sits over an in-world listbox (raised plate, bright rule, 3px corners, options divided by `rule` hairlines, the active option lifted to sand at 12% into the plate, wipe-open behind a motion preference). Full keyboard model: arrows, Home/End, Enter/Space, Escape, 500ms typeahead, outside-click close.
- **Search palette:** a modal dialog capped at 42rem, 12vh from the top, on a black 60% backdrop. A Search plate label, the field over a raised-plate results list, the active row lifted to sand at 12% into the plate, then a strip naming the selected track beside the Queue (sand, primary) and Layer keys.
- **Volume scale:** a native range restyled as a ruled scale. Sunken fill, 1px bright rule, 3px corners, a 1px tick every 4px, an amber 0.4rem thumb with 2px corners, 8rem wide in the dock and 6rem in a layer row. It is 16px tall on desktop and 44px in the dock on coarse pointers, the one native control below the 40px authored floor.

### Navigation

The panel has two surfaces and two ways of getting around. They share placards and keys, and never share a frame.

**The music page** has no nav: the placard bar is the wayfinding. It holds the wordmark placard (the pixel mark at 1.6rem beside HARPI in Urbanist 800 at 0.85rem tracking 0.24em), the output placard (guild and channel, hover-lifted), the carrier placard, the voice placard, then the Search key with its shortcut hint (Ctrl K, or the command key on a Mac, hidden under 30rem) and the Sign out key. The output placard is also the control: it opens a popover holding the Guild and Channel selects, an optional hint, and the Connect or Reconnect key beside Disconnect. Under 30rem the bar wraps and the output placard takes a full row.

**The campaign shell** frames every `/c/<campaign>/…` page. A 14rem rail runs the full viewport height, fixed, on the plate tone with a 1px bright rule on its inner edge. From top to bottom it holds:

- **The wordmark** as the way home: the pixel mark at 1.6rem beside HARPI in Urbanist 800 at 0.85rem tracking 0.24em, on a link that takes the usual 2px amber focus outline.
- **The campaign placard:** a placard stacked label over value, the claim CAMPANHA in Barlow 600 at 0.6875rem tracking 0.16em amber, and the campaign name in JetBrains Mono 0.8125rem sand, ellipsised at the rail width.
- **The pages:** MESA, PERSONAGENS, FICHA and CENAS in one column, each a 2.5rem row in Barlow 600 at 0.72rem tracking 0.14em, divided by 1px `rule` hairlines. A 0.4rem square lamp leads each row. The inactive row is dim ash with a bright-rule lamp; hover lifts the ink to sand, the fill to the raised plate and the border to oxide, exactly like a key. The active row is a raised-plate fill, a sand label and an amber lamp, and it carries `aria-current="page"`. The active row is never a sand fill: sand stays the pressed surface.
- **The link placard** at the foot of the rail: the claim LINK over the state, ATIVO in amber when the stream is live, PERDIDO in hazard red when it is reconnecting, CONECTANDO in dim ash before the first frame. It is a reading, not a control.

Below 56rem the rail turns into a band across the top. The wordmark and the campaign placard share the first row, the four page links wrap under them as a row of keys with the lamps, and the link placard takes the end of the band. The band is not fixed and scrolls away with the page; the content column starts under it. The shell's content column caps at 72rem and centres while the rail stays put; below 56rem the band is the full width of the page.

The campaign shell never carries the music dock, and the music page never carries the campaign rail. A VTT page owns its bottom edge and has no `--transport-height` to clear.

### Named Rules
**The Two Surfaces Rule.** Music and the table never share a frame: the music page keeps the placard bar and the transport dock, the campaign shell keeps the 14rem rail and no dock. A placard, a key or a reading may cross over; a fixed frame may not.

### The Seek Scale (signature)
- The seek control is a stepped amber scale in the dock: flex 1, min-width 8rem, 2.5rem tall (2.75rem on coarse pointers), sunken fill ruled with the unlit steps (7px of raised plate, 3px off), inside a 1px bright rule with 3px corners.
- **Fill:** the played span is the lit steps (7px of amber, 3px off) with 3px right corners. While paused it swaps to the caution band (7px of oxide, 5px off).
- **Interaction:** the track grabs on pointer down (grab and grabbing cursors, `touch-action: none`) and seeks to the drop point. `role="slider"` with aria-valuemin, max and now. Arrows seek 5s, PageUp and PageDown 15s, and Home and End jump to the ends. Focus takes the 2px amber outline.
- **Offline:** `aria-disabled`, a not-allowed cursor, and every gesture and key is gated.
- **Settle:** the fill eases between progress updates at 180ms ease-out so the scale drifts rather than jumps, and it snaps while the operator drags because direct manipulation is instant.

### The Transport Dock (signature)
- Fixed across the bottom edge: raised-plate fill, 1px bright rule on the top edge, 0.5rem 1rem padding, 0.5rem gaps, z-index 10.
- It holds Prev, the sand Pause or Play key, Skip, the Loop key, the seek scale, the volume scale and its value, and the readout (position and duration, then the track title in dim ash after a middle dot). The dock ends with the status strip, the panel name in faint ash.
- **Offline:** a Bot offline chip (hazard ink on the hazard well, 1px hazard-red border, 2px corners) prepends the readout, the transport keys strike out, and the carrier placard in the bar above flips.
- **Compact:** under 30rem the dock wraps. Keys share a row at `flex: 1 1 4.5rem`, the readout and the status strip hide, the seek scale takes a full-width row, and the volume control shrinks to 6rem.

### Fault Plates and Toasts
- **Fault plate:** the error region, fixed above the dock's left corner. A hazard well under a 0.4rem banded hazard strip at the top, 1px hazard-red border, 4px corners, hazard ink, and it leads with the Hazard stamp in hazard red, then the message, then Dismiss (and Refresh for a contract violation). It arrives from the left.
- **Toast:** the confirmation channel, fixed above the dock's right corner. Raised plate, 1px bright rule, a 1px amber left edge, 3px corners, Barlow 600 at 0.6875rem tracking 0.1em uppercase in sand, arriving from the right. Errors never arrive here. An undo action rides inside the toast as a small key.
- Both clear the dock through `calc(var(--transport-height) + 0.5rem)`, so a wrapped dock on a phone never covers them.

### Readouts, Gauges and Rows
- **Readout cell:** a data label (Barlow 600, 0.6875rem, tracking 0.12em, uppercase, dim ash) over its value (JetBrains Mono, sand, tabular numerals), in the rating bed.
- **Queue gauge:** a 4rem by 0.4rem stepped bar per row, filled in amber proportional to the longest queued track over the unlit step track. A readout, not a control.
- **Queue row:** a 2.75rem minimum height, the index in amber (01), a 32px thumbnail, the title, the gauge, then "uploader · duration" in faint ash and a Remove key. Rows divide with `rule` hairlines and arrive staggered.
- **Layer row:** the index, thumbnail and title, then a 6rem volume scale and a Remove key below. Rows use FLIP so removal slides the survivors instead of snapping them.
- **Linked roster:** a three-column grid of name, channel and seen time with hairline row separators.
- **Empty states:** uppercase dim-ash readouts ("Queue empty — search to add tracks.", "No layers — add one from Search.") beside the key that fixes it.

### Browser Surfaces and the Boot Plate
- **Selection:** amber background, ground text. **Caret:** amber. **Scrollbars:** thin, bright-rule thumb with a 3px ground border on a transparent track.
- **Boot:** the pixel mark at 38px beside "Linking…" in Urbanist 800 at 0.85rem tracking 0.2em uppercase in dim ash, with the mark blinking behind a motion preference.
- **Sign-in:** a plate labelled Access holding the HARPI PANEL title, the note that a shared Discord server is required, and a full-width sand CONTINUE WITH DISCORD key.

## Do's and Don'ts

### Do:
- **Do** pair every placard claim with the value that proves it. A placard with no value is a heading, not a placard.
- **Do** ink state in amber (9.2:1 on a plate) and reading text in bone or sand, and keep amber off resting surface fills.
- **Do** press sand for the primary action: the sand key, the search sheet's Queue key, the flipped carrier placard and the sign-in key each carry the printed grain and the printed edge.
- **Do** reserve the 0.4rem banded hazard strip for the carrier flip and fault plates.
- **Do** strike out keys when the carrier drops (struck gray ink, `line-through`, `rule` border) instead of hiding them.
- **Do** keep the seek scale stepped: 7px lit or unlit, 3px apart, amber when playing and oxide when paused.
- **Do** keep corners at 3px for keys and placards and 4px for plates and bars, and keep every lamp square.
- **Do** set headings and stamps in Urbanist, legends and controls in Barlow, and values in JetBrains Mono, with the smallest type at the 11px floor.
- **Do** keep depth tonal and printed: the ladder, 1px rules, the grain, the bands, and the single overlay shadow.
- **Do** clear the dock through `--transport-height` and let the dock measure itself.
- **Do** gate every blink behind `prefers-reduced-motion: no-preference`, and keep the 140ms color settles and the placard flip under it, because they carry state rather than movement.
- **Do** keep tabular numerals wherever a number can change.
- **Do** give destructive keys a quiet rest (bone ink) and let hover bring the hazard red.

### Don't:
- **Don't** reintroduce the replaced receiver world: no steel-navy plates, no phosphor-cyan ink, no sodium dial lamp, no ruled calibration scales, no square 0px-radius keys.
- **Don't** use hazard red or oxide as decoration. Hazard means breakage and oxide means caution.
- **Don't** put hazard banding on a healthy surface.
- **Don't** add a fourth font family, and never set a value or a legend in Urbanist.
- **Don't** round a corner past 4px or draw a pill, a circle or a dot.
- **Don't** add glows or gradient text. The only gradients are the hazard and caution bands, the printed grain, the stepped scales and the modal backdrops.
- **Don't** invert a key to sand unless it is the primary action or the flipped placard.
- **Don't** let the struck gray disabled ink (3.7:1) leak into readable content.
- **Don't** invent a second authored moment. The placard flip is the only one.
- **Don't** add spinners, skeletons or fake progress: waiting is text in place (Linking…, Checking…, Reconnecting…, Searching…).
- **Don't** ship the OS-native select popup or the native search-cancel button. Overlays are built in-world.
- **Don't** drop the fixed chrome below the dock or hardcode the dock height.
