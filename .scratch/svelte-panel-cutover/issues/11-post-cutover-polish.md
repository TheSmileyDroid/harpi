# 11: Post-cutover polish

**What to build:** A beauty pass over the stable architecture, judged in the browser against the project's design language. No behavior or contract changes here.

**Blocked by:** 10

**Status:** done

- [x] Every surface reviewed at desktop and mobile widths
- [x] The fixed chrome rules for status strip, transport bar, and toasts hold at mobile widths
- [x] Contrast, spacing, and interaction states are consistent with the design language
- [x] No endpoint contract or user-visible behavior changes as part of this pass

## Comments

Reviewed in Chromium against the harness app at 1280x900 and 390x844. Populated
with queue, layer, and search state so every panel rendered.

Three defects found and fixed, all CSS plus one class binding:

- Toasts collided with the transport bar. `.toast-container` sat at `3rem`
  while the transport bar starts at `1.75rem` and is taller than the gap:
  measured 24.9px overlap on desktop, 30px on mobile where the bar wraps and
  the toast landed inside it. The bar's wrapped height is width-driven (61.7px
  at 480px, 78.5px at 340-414px, 89.6px at 320px, 106.4px at 300px and below),
  so no fixed offset is correct. `TransportBar` now publishes its measured
  height as `--transport-height` (a `ResizeObserver` on the bar), and the toast
  column anchors at `calc(1.75rem + var(--transport-height, 5rem) + 0.5rem)`.
  Re-measured 0px overlap at every width from 280px to 480px.
- `:focus-visible` corner brackets were dropped in the Svelte port: the retired
  `static/css/input.css` styled `.hud-btn:focus-visible` and `.hud-input` with
  Hot Amber L-brackets, and the port kept the class names but not the rules, so
  buttons fell back to the UA ring. Restored for `.hud-btn`; inputs and selects
  are replaced elements that cannot carry pseudo-elements, so fields get a Hot
  Amber 1px outline at 2px offset instead.
- `.hud-panel.is-playing` was gone from both markup and CSS. Restored on the
  playback panel, toggling on `is_playing && !is_paused` (the new store's
  `is_playing` stays true while paused, so the `!is_paused` term reproduces the
  old panel, whose `is_playing` was false when paused).

`DESIGN.md` updated to match the shipped chrome and focus behavior.

Verified: `make check` exit 0, every gate ran (pytest 558 passed, coverage
95.52%; jscpd 0 clones; svelte-check 0 errors; vitest 67 passed; knip clean;
Playwright 8 passed). No endpoint, contract, or behavior change.
