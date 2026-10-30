# ADR 0011: Campaign state lives in SQLite, with authored and snapshot copies in the vault

## Context

A campaign has two kinds of state with different owners. The scene, the
fog, the tokens, the turn and the dice log change many times per minute
while a session runs. The character notes, the sheet blocks, the campaign
config and the scene blueprints are authored by people in Obsidian and
must stay readable and editable there, offline, on any device the vault
syncs to.

Writing live state into the vault would put a 10 Hz writer against
Syncthing and the Obsidian autosave. Keeping the authored files only in
SQLite would take the vault away from the people who already work in it.
The table also needs to survive a restart and a lost database.

## Decision

Split the state by ownership and write each half in the medium that fits
it.

- SQLite, the panel database, is the live truth: campaigns, members,
  tables, the working copy of scenes, zones and fog, tokens, turns,
  rolls, approvals, sheet sync state, sheet conflicts and character
  visibility.
- The vault holds authored artifacts under `Harpi/Campaigns/<slug>/`:
  `config.md`, `characters/`, `sheets/`, `assets/`, `scenes/<slug>.json`
  (image, grid, zones, initial fog, no tokens) and `tables/<table-id>.json`
  (the periodic snapshot).
- A scene enters a Table by being copied from its blueprint into
  SQLite. The blueprint stays the authoring surface and the SQLite row is
  what the session edits. Reimport compares `blueprint_hash`: a zone with
  the same id keeps its live reveal state, a new zone starts hidden, a
  removed zone loses its fog.
- A scene edit never applies live. The table warns that the file changed
  and the narrator reloads the scene explicitly.
- Opening a table is guarded by two partial unique indexes, one on the
  campaign and one on the channel, so a second open table is a database
  conflict rather than application bookkeeping.
- Closing a table ends the turn and the round, writes the snapshot, and
  only then marks it closed. A closed table without a snapshot cannot
  exist.
- The snapshot is written every 60 s and on structural change with a 2 s
  debounce, by a single writer per table, and read in a consistent
  transaction before being written outside it.
- After a crash the table stays open and SQLite wins. The periodic
  snapshot is a safety net for database loss, never a concurrent source
  of truth. Restoring a closed table validates version, kind, table and
  campaign, and repopulates the current scene, its fog, its tokens and
  the round.
- The app never renames, moves or deletes a vault file. Overwriting a
  blueprint or snapshot atomically is the only write.

## Consequences

- A session restart resumes from SQLite, including tokens, fog, round and
  the dice log.
- Losing the database leaves the blueprints, the sheets and the last
  snapshot. Rolls, approvals and conflicts are only in the database and
  its daily backups.
- A scene can be prepared in the editor with the table open, but the
  table only picks it up on reload. That delay is deliberate: preparation
  and play are different moments.
- The vault stays a plain Obsidian folder. Nothing in it is a lock, a
  journal or a hidden index.
- A local campaign in M2 swaps the sheet store and the asset resolution,
  not the SQLite schema or the routes.
