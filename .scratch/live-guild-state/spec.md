# Live guild state, panel roster, SQLite registry

## Problem

The panel keeps a guild selection in a signed cookie that only changes on
connect. A user who merely picks a guild in the output picker never tells
the server, so their stream can resolve to another guild. A connection
made by one member does not move the other members' channel selection,
and the channel list is fetched once.

There is no record of who is using the panel, which channel they are
looking at, or who connected and released the bot. Everything is lost on
restart.

## Goal

- A connection made by any member in a guild is visible to every user
  watching that guild within one SSE poll, and the panel follows the
  connected channel automatically.
- The panel shows who is linked to the selected guild and who made the
  last connect or disconnect.
- Selections and the roster survive a restart, backed by a relational
  store that starts small and can grow with normal SQL.

## Decisions

- **SQLite in the process.** `aiosqlite` over one WAL database file.
  Versioned SQL migrations in `src/storage/migrations/`. No service to
  run for a self-hoster. See ADR 0008.
- **Selection is server state.** `POST /api/selection` persists the
  guild and channel for the signed-in user and updates the session
  cookie. Clearing the selection drops the viewer row. The SSE stream
  then follows the same guild the panel shows; a change of guild restarts
  the stream.
- **Presence is a frame, not a status field.** A new `presence` SSE event
  carries the roster and the last connection event. It is emitted on
  stream open and on the five-second presence heartbeat when the roster
  or its recency changes, never on every 0.5s status poll.
- **A viewer is fresh for 30 seconds.** The stream refreshes their
  `last_seen_at` on the heartbeat; a closed tab disappears without a
  disconnect hook.
- **Auto-follow stays inside the selected guild.** A connection made in
  that guild moves the panel's channel selection to the connected channel
  and reloads the channel list when the channel is new. A connection in
  another guild does not move the guild selector.
- **The last connection event is the registry's "who".** Connect and
  disconnect record the actor from the OAuth session. A bot-side connect
  or an unexpected leave does not invent an actor.
- **The registry degrades without blocking playback.** If storage is not
  initialized, panel state, playback, and transport keep working and the
  roster is empty. Startup logs the failure.

## Wire

- `POST /api/selection` `{guild_id, channel_id}` answers `StatusSnapshot`.
- SSE `presence` answers
  `{guild_id, viewers[], last_connection}`.
- `Viewer` carries `user_id`, `username`, `display_name`, `channel_id`,
  `channel_name`, `seen_at` (epoch seconds).
- `ConnectionEvent` carries `action`, `channel_id`, `channel_name`,
  `actor_id`, `actor_name`, `at`.

## Files

- `src/storage/` — database, migrations, registry.
- `src/config.py` — `HARPI_DB_PATH`.
- `app.py` — open the database at startup.
- `src/panel/{schemas,serialization,state}.py` — presence seam.
- `pages/{api,events,auth}.py` — selection route, presence frame, actor.
- `web/src/lib/` — store, SSE, API client, roster component, picker
  follow.
- `docs/adr/0008-sqlite-panel-registry.md`.

## Out of scope

- Storing playback history, queue, or tracks.
- A migration tool beyond ordered SQL files.
- Multi-process deployments sharing one database file.
