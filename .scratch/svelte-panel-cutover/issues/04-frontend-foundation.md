# 04: Frontend foundation

**What to build:** The Svelte app shell exists and proves the whole path end to end: sign in, see live bot and playback status, watch it update without reloading, survive a dropped stream, and surface confirmations transiently and failures persistently.

**Blocked by:** 01, 03

**Status:** ready-for-agent

- [x] The sign-in flow establishes the session and the session persists across a backend restart
- [x] The status surface renders guild, connection, and playback state from server truth
- [x] SSE updates change the UI, and background updates show no loading treatment
- [x] A dropped stream reconnects and state recovers without a manual reload
- [x] Toast and persistent error primitives exist and the surface uses them
- [x] Vitest units cover the client store and SSE reducer; one Playwright critical path proves sign-in plus a live update
