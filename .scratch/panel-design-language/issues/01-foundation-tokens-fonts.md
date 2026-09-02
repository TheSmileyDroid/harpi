# 01: Foundation — tokens OKLCH + font swap

**What to build:** The whole panel adopts the design doc's palette and type stack in one pass: the twelve OKLCH tokens from `docs/agents/design.md` (near-black background, phosphor amber accents, red reserved for alerts), the subtle vignette added to the existing global scanline overlay, and body/display type moved to IBM Plex Mono + Rajdhani (semibold, uppercase, wide tracking for display). Old fonts leave the imports and theme variables. The panel is immediately demoable in its new colors.

**Blocked by:** None (can start immediately).

**Status:** ready-for-agent

- [ ] Theme source defines exactly the doc's token table; nothing references the removed fonts.
- [ ] Scanline overlay gains the subtle vignette in the same fixed layer, still `pointer-events: none` and guarded by `prefers-reduced-motion`.
- [ ] Tailwind build compiles clean and the compiled CSS contains the new tokens.
- [ ] Quart-client tests assert rendered pages carry no stale-font references; `make format` and `make check` exit 0.
- [ ] Playwriter loop (run the panel with `make dev`): screenshots of every page confirm amber-on-near-black rendering and both font families applied.
