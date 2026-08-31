# 02: The panel's guild list tells the truth

**What to build:** Every panel request computes the guild list from the live bot handle. A guild the bot joins, or a reconnection, is visible on the next request with no cache in between. The unreachable guard after the bot-handle lookup (which already asserts non-None) is deleted.

**Blocked by:** None (can start immediately).

**Status:** ready-for-agent

- [ ] The module-level forever-cache and its None sentinel are gone; the guild list is computed per request.
- [ ] A page-handler test proves the list changes when the bot's guild set changes between two requests.
- [ ] The first request after boot shows the correct guild list.
- [ ] The dead `if not bot` branch after the assert-based lookup no longer exists.
- [ ] `make format` then `make check` passes.
