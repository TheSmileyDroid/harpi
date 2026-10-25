# 12: Owner-only !shutdown

**What to build:** Only the bot owner can run `!shutdown`. Any other member is refused, and the bot stays up.

**Blocked by:** None (can start immediately).

**Status:** ready-for-agent

- [ ] The command checks the bot owner's Discord ID.
- [ ] A non-owner receives a refusal and the bot stays up.
- [ ] The owner can still shut the bot down.
- [ ] A test covers the owner and non-owner paths.
- [ ] Demo: a guild member runs `!shutdown` and is refused.
