# ADR 0015: The VTT surface is removed; the bot is music, dice and TTS again

## Context

ADR 0010 through ADR 0014 built a virtual tabletop inside the panel: live
tables with tokens, fog and turns (0010), campaign state in SQLite (0011),
character sheets kept in sync with a vault of Markdown files (0012),
per-campaign authorization derived from sheets (0013), and the Fate sheet
format (0014).

That surface outgrew the product. `PRODUCT.md` describes a Discord bot for
music, dice and TTS with one panel for controlling the music; the VTT
arrived afterwards and came to dominate the repository: 20 of the 31 files
under `src/panel/`, 43 of the 70 blueprint routes, the whole campaign tree
of the Svelte app, and roughly 15k lines of tests. It also carried a
dependency (`watchdog`), a second configuration axis (`HARPI_VAULT_PATH`,
`HARPI_NARRATOR_ID`, `HARPI_GUILD_ID`), and a write path that rescanned the
whole vault on every sheet edit.

Keeping it half-alive was worse than removing it: with tables gone, a
campaign surface would still create scenes and sheets that nothing reads.

## Decision

Delete the VTT surface instead of freezing it.

- Removed: `pages/campaigns.py`, `pages/tables.py`, and the `src/panel/`
  modules for tables, table streams, scenes, rolls, sheets, sheet writes,
  sheet merges, conflicts, notices, cast, campaigns, enrollment, assets,
  vault, vault index, vault sync, vault write, notes, and character notes.
- Removed from the panel: the campaign route tree, the campaign shell, the
  table map, the sheet editor, the conflict queue, and their TypeScript
  modules and tests. The music page is the only frame again.
- The dice roller stays. It no longer mirrors rolls into the panel: the
  mirror only recorded a roll while a table was open in the channel, and
  so had no meaning without tables. `run_on_panel_loop` was removed with
  it, leaving `run_on_bot_loop` as the only loop bridge.
- Migration `0011_drop_vtt.sql` drops `campaigns`, `members`,
  `sheet_files`, `sheet_conflicts`, `character_visibility`, `approvals`,
  `assets`, `scenes`, `tables`, `tokens`, `turns`, `rolls` and
  `sheet_notices`. Migrations 0004 through 0010 stay: they are history,
  and a database that already ran them needs the drop in a later file.
- The registry (ADR 0008), presence, retention, backup, the generated
  contract (ADR 0004), the live panel stream (ADR 0009) and the OAuth
  login (ADR 0007) keep working unchanged.
- Vault files on disk are never touched by the code. The operator keeps or
  deletes them by hand.

ADRs 0010, 0011, 0012, 0013 and 0014 are superseded. Their reasoning about
tables, sheets and campaigns no longer describes the system.

## Consequences

- `src/panel/` is nine modules and one job: the shared domain seam for
  music state.
- The app answers 32 routes, and the 27 that belong to blueprints are all
  music, session, presence or auth.
- One fewer dependency, three fewer environment variables, and no
  filesystem watcher in the process.
- A database created before this change keeps its registry rows and loses
  its VTT rows on the next boot.
- Rebuilding any of it would start from these ADRs, not from the deleted
  code.
