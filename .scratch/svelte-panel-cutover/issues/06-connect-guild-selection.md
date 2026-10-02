# 06: Connect and guild selection

**What to build:** Guild selection and voice connection work in the new UI, end to end, against the real API.

**Blocked by:** 05

**Status:** ready-for-agent

- [x] The guild selector lists only guilds the bot shares, matching bot state
- [x] Selection persists for the session
- [x] Connect joins the selected guild's voice channel; disconnect leaves it
- [x] State after each action reflects server truth rather than optimistic UI
- [x] pytest covers the endpoints; a Playwright path covers connecting

## Comments

Schema frozen here, per `spec.md` "Reserved for tickets 06 to 09":

- `GET /api/guilds` -> `200 {"guilds": [{"id": int, "name": str}]}` from `state.list_guilds()`.
- `GET /api/guilds/<guild_id>/channels` -> `200 {"channels": [{"id": int, "name": str}]}`; `404 not_found` when the bot does not share the guild.
- `POST /api/connect` `{"guild_id": int, "channel_id": int}` -> connects through `actions.connect`, writes the session selection, and answers `200` with the fresh `status_snapshot`. An unknown guild, a channel outside the guild, or a missing/non-integer field answers `404 not_found`.
- `POST /api/disconnect` -> disconnects when a session exists, is a no-op when it does not, keeps the selection, and answers `200` with the fresh `status_snapshot`.

Deliberate decisions:

- Selection is written on connect and kept on disconnect. It lives in the signed session cookie, so it survives a backend restart. A guild picked in the dropdown but not yet connected is client state (`pendingGuildId`), separate from the server selection (`guildId`).
- `state.status_snapshot` drops a selection the bot no longer shares, so a stale cookie never reads as a live guild. This preserves the old panel's stale-cookie behavior.
- `GET /api/events` captures the selection once, when the stream opens. The client restarts the stream after connect and disconnect so live frames track the new selection instead of the pre-connect one.
