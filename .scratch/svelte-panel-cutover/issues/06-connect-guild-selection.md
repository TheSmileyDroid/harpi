# 06: Connect and guild selection

**What to build:** Guild selection and voice connection work in the new UI, end to end, against the real API.

**Blocked by:** 05

**Status:** ready-for-agent

- [ ] The guild selector lists only guilds the bot shares, matching bot state
- [ ] Selection persists for the session
- [ ] Connect joins the selected guild's voice channel; disconnect leaves it
- [ ] State after each action reflects server truth rather than optimistic UI
- [ ] pytest covers the endpoints; a Playwright path covers connecting
