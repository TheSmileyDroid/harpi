# ADR 0008: SQLite panel registry

## Context

The panel has per-user state (the selected guild and channel) and shared
state (who is connected in a guild and who made the last connection).
Until now the selection lived in a signed cookie and disappeared from
anything the server could query. The panel also needs a roster that
survives a process restart.

The deployment target is a self-hoster running one process from a repo
clone, with Docker Compose as the documented production path. Adding a
database service raises the setup cost for that audience.

## Decision

Use SQLite through `aiosqlite`, one database file per process, in WAL
mode, with ordered SQL migrations under `src/storage/migrations/` and a
`SqliteRegistry` implementing the small `Registry` seam.

- The file path comes from `HARPI_DB_PATH` (default `data/harpi.db`).
- Migrations are numbered files applied in order and recorded in
  `schema_migrations`; no migration framework.
- The registry records users, guilds, voice channels, the current viewer
  selection with a heartbeat timestamp, and connection events.
- Presence is read with a 30-second freshness window, so a closed tab
  ages out without a disconnect callback.
- The registry is optional at the domain seam: if it is not initialized
  (tests, a failed open) playback and transport still work and the
  roster is empty. Startup logs the failure.

## Consequences

- A self-hoster keeps one process and one directory. Backups are a file
  copy.
- SQLite's single writer bounds concurrent panel traffic, which is
  acceptable for one guild-scale deployment. A future multi-instance
  deployment would swap the `Registry` implementation, not the schema.
- The database is not a playback store. Queue and history remain in the
  session, so a restart still ends playback.
- History beyond the last connection event is kept in the table but not
  exposed on the wire yet. Adding it is a query and a contract field.
