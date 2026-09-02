# 04: Console home + status chip

**What to build:** The home page becomes a console in the same language as music: cards with double borders and boxed titles, actions in a segmented bottom strip, telemetry-style data rows. The bot status chip adopts the new tokens: connected glows steady amber, offline glows red and blinks — red appears nowhere else on the page.

**Blocked by:** 02 (bracket on the current nav item and focused card).

**Status:** ready-for-agent

- [ ] Home cards: double borders, boxed titles, segmented action strip, right-hand metadata where lists appear.
- [ ] Status chip: amber steady when online, `alert` red + blink only when offline (with the existing reduced-motion guard).
- [ ] Whole home page contains no red outside the offline/error surfaces.
- [ ] Quart-client tests assert home and status markup carry the new structure and states (fake bot both ways, prior art exists).
- [ ] Playwriter loop (`make dev` running with the test bot): capture the chip online; capture offline however the test guild allows (or via the fake-bot page test); `make format` and `make check` exit 0.
