# 07: Closing pass — conformance gates and visual review pack

**What to build:** The whole migration lands green and reviewable: `make format` then `make check` exit 0 on the final tree, and a review pack of desktop + mobile captures of every page is produced so the maintainer can judge fidelity against the reference images (the taste call is human; the mechanical violations were already caught in-loop).

**Blocked by:** 05, 06.

**Status:** ready-for-agent

- [ ] `make format` and `make check` exit 0 with no skipped or lowered gates.
- [ ] Review pack saved: desktop and mobile captures of home, music (idle and playing), and the offline state.
- [ ] Each capture shot at the same viewport sizes so the maintainer can compare against `references/` side by side.
- [ ] Any known deviations from the design doc are listed explicitly in the ticket comments rather than left silent.

## Agent deviations (explicit, not silent)

- **Playing/offline captures missing from the review pack.** The test bot is
  online and idle in the test guild; there is no live way to render a playing
  state or the offline chip in a browser here. Both states are covered by the
  fake-bot Quart-client tests (`bot-offline` present only when broken,
  `is-playing` bracket class on/off). Captures shipped: home desktop/mobile/
  tablet, music idle desktop/mobile.
- **Playing bracket sits on the Now Playing panel** (`.hud-panel.is-playing`),
  not on a queue row: the queue holds upcoming tracks, the playing track lives
  in Now Playing. Ticket 03's "playing row bracketed" is read as the panel.
- **Per-action loading feedback** uses htmx's automatic `.htmx-request` class
  on the triggering button (CSS blink, reduced-motion guarded) instead of a
  literal `hx-indicator` attribute; same mechanism, no attribute needed.
- **Silent polling** is achieved by absence: poller fragments carry no
  entrance animation or skeleton, so an unchanged swap renders identically.
  No diffing/morph extension was added.
- **Visual loop** ran through headless Chromium (playwright) instead of the
  `/playwriter` skill; the browser-driving client was unavailable.
- **Known taste-level debt** (reviewer-flagged, left for the maintainer): the
  music page repeats the row+meta+action markup shape three times (jscpd
  gate passes at 0 clones); `.row-meta` doubles as row index and metadata
  column.
