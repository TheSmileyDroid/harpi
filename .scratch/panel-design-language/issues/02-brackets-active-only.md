# 02: Brackets only on the element under operation

**What to build:** Corner brackets become a state signal instead of decoration: resting panels lose their brackets entirely; brackets appear on the currently focused/active element (keyboard focus, current nav item, playing queue row, pressed control). A bracket on screen answers "what is under operation right now?" and nothing else.

**Blocked by:** 01 (foundation tokens/fonts — brackets use `amber-bright`/`line-strong`).

**Status:** ready-for-agent

- [ ] Resting panels and cards render with double borders, no brackets.
- [ ] Keyboard focus-visible shows brackets; current nav item shows brackets; the playing row shows brackets.
- [ ] Quart-client tests assert bracket classes are absent at rest and present on the active element.
- [ ] Playwriter loop (`make dev` running): tab through the panel and confirm brackets follow focus; confirm a resting page shows zero brackets.
