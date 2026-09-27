# 08: Transport, seek, volume

**What to build:** Transport control with live position, and seek and volume that feel immediate.

**Blocked by:** 07

**Status:** ready-for-agent

- [ ] Play, pause, skip, previous, and loop act on the session
- [ ] Position updates arrive over SSE and the UI advances without polling
- [ ] Seek works by click and by drag, sends absolute seeks, and does not fight incoming updates mid-drag
- [ ] Volume changes are debounced and reflected in state
- [ ] pytest covers the endpoints; a Playwright path covers a transport interaction with live position
