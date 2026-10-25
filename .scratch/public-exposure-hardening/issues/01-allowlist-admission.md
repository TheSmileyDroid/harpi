# 01: Allowlist admission and persisted guilds

**What to build:** A guild member from one of the two allowlisted guilds can sign in and is recorded with the guilds they may use. A member outside the allowlist is denied, and an empty or malformed allowlist denies everyone. The allowed guild set survives a restart and is available to the API.

**Blocked by:** None (can start immediately).

**Status:** ready-for-agent

- [ ] `PANEL_GUILD_ALLOWLIST` accepts the two Snowflakes and rejects malformed values.
- [ ] Login intersects the user's guilds, the allowlist, and the bot's guilds.
- [ ] An empty or malformed allowlist denies every login and never falls back to all bot guilds.
- [ ] A denied login redirects to `/?auth=denied`; an allowed login establishes `authenticated`.
- [ ] The allowed guilds are persisted in the registry and survive a restart.
- [ ] HTTP-seam tests with fake Discord cover allowed, denied, empty, and malformed cases.
- [ ] Demo: one user from each allowlisted guild signs in; a third user is denied.
