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

**The Posted Placard.** The panel is a placard board for a working guild, not a
dashboard. Every state is a placard: a claim in Barlow small caps paired with the
value that proves it in JetBrains Mono, pressed into a plate-toned tag. The board
is warm near-black (`#14110d`) under plate tones (`#1f1b15`, `#2a241c`).

It refuses the card grid: placards pack to their edges and divide with 1px rules
instead of gaps. Materials carry the identity: sand (`#e9dfc7`) is what the
operator presses, amber (`#f2b24e`) is the state lamp, oxide (`#ce7442`) is
caution, hazard red (`#f0604a`) means breakage. Corners are 3px on keys and
placards, 4px on plates and bars, 1px on instrument bits. Nothing glows, no text
is gradient-filled, and one drop shadow exists in the whole system.

## Colors

- **State Amber** `#f2b24e` — the state lamp and every live reading: placard
  legends, the state stamp, the seek scale and its fill, the volume value,
  indices, hover ink. 9.2:1 on a plate.
- **Placard Sand** `#e9dfc7` — the pressed material and the ink of titles: the
  primary key, the search sheet's Queue key, the flipped carrier placard, the
  sign-in key, track titles, readout values. 12.9:1 on a plate.
- **Oxide Caution** `#ce7442` — hover borders and the seek fill while paused.
  5.1:1 on a plate.
- **Hazard Red** `#f0604a` — breakage only: offline chip and lamp, stale tag,
  Perigo stamp, fault-plate borders, search failure text, hazard band stripes.
  5.3:1 on a plate. **Hazard Well** `#2a1712` beds it; **Hazard Ink** `#d9c7b4`
  is the readable ink on it (10.4:1).
- **Neutrals** — ground `#14110d`, placard plate `#1f1b15`, raised plate
  `#2a241c`, sunken well `#0d0b08`, rating bed `#191510`, bright rule `#3d3527`,
  bone label `#c4b79d` (9.5:1), dim ash `#a59a8a` (6.2:1), faint ash `#948a79`
  (5.0:1), sand ink `#221e18` (12.5:1 on sand), struck gray `#7d7365` for
  disabled ink only (3.7:1, never readable content).

**Rules.** Amber is a lamp, never body copy and never a resting fill. Banded
hazard appears only when the carrier drops and on a fault plate; oxide stays a
caution band and a hover border. Only the primary key, the search sheet's Queue
key, the flipped carrier placard and the sign-in key are sand, each with printed
grain and a printed edge.

## Typography

Three faces with one job each: **Urbanist** headings and the two stamps,
**Barlow** legends, controls and prose, **JetBrains Mono** values, metadata,
inputs and indices. Nothing else. No value in Urbanist, no heading in Mono.

| Role | Face | Size / weight / tracking |
| --- | --- | --- |
| Display | Urbanist | 0.95rem 800, 0.16em, uppercase |
| Headline | Urbanist | 1.375rem 700, -0.01em |
| Plate | Urbanist | 0.75rem 700, 0.18em, uppercase |
| Stamp | Urbanist | 0.8125rem 800, 0.14em, uppercase |
| Placard / Link | Barlow | 0.6875rem 600, 0.16em, uppercase |
| Control | Barlow | 0.72rem 600, 0.14em, uppercase |
| Label | Barlow | 0.6875rem 600, 0.12em, uppercase |
| Value | Mono | 0.8125rem 400 |
| Meta | Mono | 0.75rem 400 |

The state stamp (TOCANDO, PAUSADO, PARADO) is always amber and reports
playback; the carrier's health is the stale tag's job. The Perigo stamp is
hazard red. The smallest type anywhere is 11px. Tabular numerals wherever a
number can change.

## Layout

One column capped at 72rem, padded 0.75rem top, 1.25rem sides and
`calc(var(--transport-height) + 1.5rem)` bottom so the dock never covers
content. The console splits at 56rem into a fluid main column (Tocando agora
over Fila) and a 15.5rem rail (Camadas, Sessão, Conectados), collapsible behind
Ocultar camadas. The rating grid auto-fits at `minmax(7rem, 1fr)`. The queue
caps at 60vh and scrolls. Fixed chrome stacks above the dock: toasts (60),
error region (65), output popover (40), select list (50), dock (10), and every
fixed surface clears the dock through `--transport-height`.

Breakpoints: 30rem is the compact collapse (bar wraps, dock wraps, art drops to
4rem); 48rem caps the dock readout at 22ch; 56rem splits the console. Coarse
pointers raise authored controls to 2.75rem. The world never switches off:
density collapses, the placards stay.

Spacing: 0.35rem inside rows, 0.5rem between placards, 0.75rem inside clusters,
0.85rem from a band to its content, 1rem between panels, 1.25rem gutters.

**Rules.** The dock measures itself with a ResizeObserver and publishes
`--transport-height`; a hardcoded dock height is a bug. Placards and rating
cells pack to their edges and divide with hairlines; gaps separate plates, never
cells inside one bed.

## Elevation, Shapes, Motion

Depth is a tonal ladder (sunken, rating, ground, plate, raised plate), 1px rules,
printed material (hazard band, grain, stepped scales) and dimmed backdrops.
Exactly one drop shadow exists: the output popover's lift. Sand surfaces carry
the printed edge instead; rating cells share inset hairlines.

Keys, placards, inputs, selects, toasts, thumbnails and the seek track take 3px;
panels, bars, popovers, dialogs and fault plates 4px; lamps and gauges 1px, the
volume thumb 2px. No pills, no circles: the carrier lamp is a 0.4rem square, the
select chevron a rotated 0.4rem square, thumbnails 48/32/96px squares.

Motion is one authored moment: when the carrier drops, the carrier placard
inverts to sand under a 0.4rem banded hazard strip and the transport keys strike
out. Everything else is arrival, a 140ms color settle, or a gated blink. Every
blink and the flip sit behind `prefers-reduced-motion: no-preference`. No
spinners, skeletons or fake progress: waiting is text in place (Vinculando…,
Verificando…, Reconectando…, Buscando…).

## Components

- **Placard** — 3px, raised plate, min-height 2.5rem, claim in amber over value
  in sand mono, ellipsised, never empty. The bar is a raised band holding the
  wordmark, output, carrier and voice placards, then Buscar and Sair. Flipped,
  it inverts to sand with sand ink, because hazard red on sand is 2.4:1.
- **Key** — 3px, 1px bright rule, transparent fill, min 2.5rem × 3.5rem, Barlow
  control, bone ink. Hover lifts ink to sand, fill to raised plate, border to
  oxide; focus-visible draws a 2px amber outline. Primary is sand with printed
  grain and edge. Danger rests quiet and floods the hazard well on hover.
  Disabled strikes out (struck gray, `line-through`). Row keys and fault-plate
  keys shrink to 2rem; coarse pointers raise keys and inputs to 2.75rem.
- **Chips** — carrier lamp plus label (NO AR amber, FORA DO AR hazard red with a
  1s `steps(2)` blink); link state (VÍNCULO ATIVO amber, PERDIDO hazard red,
  VINCULANDO dim); stale tag DESATUALIZADO in hazard red, which also dims
  readouts to 45% while every control stays live.
- **Panels** — placard plate, 1px bright rule, 4px, 1rem padding, with a plate
  band trailing a 1px rule. The rating plate is a bed of cells divided by inset
  hairlines.
- **Inputs** — sunken well, 1px bright rule, 3px, sand text; focus draws the 2px
  amber outline. Selects are in-world listboxes (arrows, Home/End, Enter/Space,
  Escape, 500ms typeahead, outside-click close), never the native popup.
- **Seek scale** — stepped amber: 7px lit, 3px off, oxide while paused, 2.5rem
  tall, `role="slider"`, arrows 5s, PageUp/Down 15s, Home/End, 180ms settle
  between updates and instant while dragging.
- **Transport dock** — fixed, raised plate, 1px top rule: Prev, sand Pause/Play,
  Skip, Loop, seek, volume, readout, status strip. Offline prepends a hazard
  chip and strikes the keys; under 30rem it wraps.
- **Fault plate** — hazard well under a banded strip, hazard red border, Perigo
  stamp, message, Dispensar (and Recarregar for a contract violation), arriving
  from the left. **Toast** — raised plate, amber left edge, confirmation only,
  arriving from the right.
- **Rows** — queue row with amber index, 32px thumbnail, gauge and Remover key;
  layer row with a 6rem volume scale and FLIP removal; Conectados as a
  three-column roster. Empty states are uppercase dim-ash readouts beside the
  key that fixes them.
- **Browser surfaces** — amber selection and caret, thin bright-rule scrollbars.
  Boot is the mark beside Vinculando…; sign-in is an Access plate with a
  full-width sand CONTINUE WITH DISCORD key.

## Don't

- Reintroduce the receiver world: no steel-navy plates, phosphor-cyan ink,
  sodium lamp, calibration scales or 0px keys.
- Use hazard red or oxide as decoration, or band a healthy surface.
- Add a fourth family, a pill, a circle, a glow, gradient text, or a second
  authored moment.
- Invert a key to sand unless it is primary or the flipped placard.
- Let struck gray leak into readable content, or ship the native select popup.
- Drop the fixed chrome below the dock or hardcode the dock height.
