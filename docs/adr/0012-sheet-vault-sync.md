# ADR 0012: Sheet sync with the vault by hash and three-way merge

## Context

Two writers share every sheet file and neither knows the other. The panel
writes the mechanical state during a session; Obsidian rewrites the whole
note from its buffer on autosave; Syncthing delivers edits made on another
device while the process was down. A player marking stress boxes while the
narrator's Obsidian autosaves would lose the marks on every pass, because
the autosave carries the stale block.

A lock file is not an option. A lock in a synced folder becomes garbage
when one side dies, and Obsidian does not respect it anyway.

## Decision

Treat the file hash as the truth of change and merge at field level.

- `sha256` of the whole file on the last accepted read is the detector.
  `harpi-rev` is only the stamp of the last app write; it never detects
  anything.
- Watch `Harpi/Campaigns/` with inotify through `watchdog` and a 500 ms
  debounce per path, plus a full scan at boot and every 60 s comparing
  `mtime` and size. The scan covers a lost event, a Syncthing rename and
  a bind mount that delivers nothing.
- Allowlist only `characters/*.md` and `sheets/*.md`. `config.md` is read
  and never merged. Dotfiles, `*.tmp`, `~syncthing~*` and
  `*.sync-conflict-*` are ignored. A Syncthing conflict file stays on disk
  for the narrator to resolve in Obsidian; the app never picks a winner.
- Keep the last accepted text, hash and parsed base per file in
  `sheet_files`, and merge in three ways: base is the last accepted
  version, ours is what the panel wants to write, theirs is the file now.
- Item identity in a list is its label, never its position: `label` for
  aspects, `name` for skills and stunts, `track` plus box value for
  stress, `severity` for consequences, `kind` plus `name` for extras,
  `item` for inventory. Renaming a key is a removal plus an addition and
  only conflicts when the other side touched the same item.
- Write surgically: only `tipo`, the `harpi-*` keys, the `harpi-sheet`
  block and the two prose sections the app owns. Everything else stays
  byte for byte, and YAML round-trips through `ruamel.yaml` to keep
  comments, order and quoting.
- Write atomically through `.harpi-tmp-<pid>`, `flush`, `fsync` and
  `os.replace`. Before overwriting, copy the previous bytes to
  `data/vault-backups/<slug>/<harpi-id>/<rev>-<timestamp>.md`, keeping 20
  per file, outside the vault and outside Syncthing.
- Compare and swap: the hash read at the start is checked again at write
  time, with up to three remerge attempts. A failure becomes a conflict.
- A field changed on both sides to different values is a conflict for
  that field. The file on disk is not touched, the sheet turns read-only
  for everyone including its owner, and the panel shows base, vault and
  panel side by side with `use vault`, `use panel` and, for text, `keep
  both`.
- Conflicts live only in SQLite. No marker goes into the file, because
  writing one would touch the disk at the exact moment the disk must stay
  intact.
- State per file is `ok`, `conflito`, `ausente`, `invalido` or
  `desconhecido`. A missing file serves its last snapshot read-only until
  someone chooses `restore` or `forget`; the app never restores by itself.
- App-owned keys are `harpi-id`, `harpi-campanha` and `harpi-owner`.
  Hand edits are ignored and corrected on the next write, with a warning.
  `harpi-status` is accepted when the transition is legal.

## Consequences

- A live session no longer loses marks to an Obsidian autosave; the worst
  case is a visible field conflict.
- Prose, headings, wikilinks, embeds, unknown frontmatter keys, comments
  and item order survive every app write.
- The app gains `ruamel.yaml`, because `pyyaml` would flatten the block
  and lose exactly what this decision protects.
- Editing the same field in both places needs a human. That is the price
  of not choosing for them.
- Backups are rotation, not history: 20 versions per file, enough for a
  session, not an archive.
- A deleted sheet is not resurrected automatically, so an intentional
  deletion in Obsidian stays deleted.
- Each file of a character-sheet pair syncs on its own; the character can
  be `ok` while the sheet is in conflict.
