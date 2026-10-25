# 03: Cross-tenant guild authorization

**What to build:** A viewer sees and controls only the allowlisted guilds they belong to. Every guild-scoped API path enforces the same rule, and an unauthorized guild answers as not found instead of revealing that it exists.

**Blocked by:** 01. Allowlist admission and persisted guilds.

**Status:** ready-for-agent

- [ ] One actor-aware visibility check is used by the guild list, channel list, connect, selection, and transport paths.
- [ ] `GET /api/guilds` returns only the guilds the actor may use.
- [ ] Unauthorized channel, connect, selection, and transport requests return `404 not_found`.
- [ ] Authorized behavior and the existing response contract stay unchanged.
- [ ] Tests cover cross-tenant denial and allowed access.
- [ ] Demo: two users in different allowlisted guilds each see and control only their own guild.
