# ADR 0014: Fate sheet as a fenced YAML block plus campaign config

## Context

Paratheos is Fate Core adapted: numeric skill ranks on a ladder, labelled
aspects, stress tracks made of boxes, consequence slots by severity,
refresh, fate points, extras such as Noética, EGO and runas, and an
inventory linked to item notes. Players create sheets from the panel,
everyone reads them in Obsidian, and the sync merges field by field
(ADR 0012). The vault already holds prose sheets written by hand, and the
dice parser already evaluates `4dF`.

A sheet format must survive three writers: the panel, Obsidian and the
sync merge. It must also be readable by a person who only knows the game,
and it must not need a schema migration when a campaign renames its
aspect labels.

## Decision

Keep the mechanical state in one fenced YAML block and let a per-campaign
config block define the rules.

- A ` ```harpi-sheet ` block holds `refresh`, `fate_points`, `aspects`,
  `skills`, `stunts`, `stress`, `consequences`, `extras` and `inventory`.
- Skills store a numeric `rank` and list only skills at 1 or above; an
  absent skill is 0. The label (`Ótimo`, `Bom`) comes from the ladder in
  the campaign config, so the file never stores a display word.
- Aspects are a list of `{label, text}`, defaulting to `Conceito`,
  `Problema` and three `Aspecto`. A campaign can rename the labels
  (`Função`, `Falha`, `Identidade`, `Conexão`, `Ambiguidade`) without a
  schema change.
- Stress is a list of tracks with boxes, each `{value, checked}`. The
  tracks come from the config; an extra may add a box with an explicit
  value.
- Consequences are one entry per config slot, keyed by `severity`, with
  the displayed `value` and a `text` that is empty while the slot is free.
- Extras are an open list with a `kind` from the config and optional
  `name`, `text` and `cost`. The app displays them and does not implement
  their mechanics.
- Inventory is `{item, qty, note}`, where `item` is a wikilink to a vault
  note. A dead link renders as text.
- A ` ```harpi-campaign ` block in `config.md`, edited only in Obsidian,
  defines name, system, ladder, skills, aspect labels, stress tracks,
  consequence slots, refresh and extra kinds.
- Prose the app owns lives in two sections after the block,
  `## História` and `## Anotações`. The app writes nowhere else.
- Unknown keys survive every write; the app edits only the block, the two
  sections and its own frontmatter keys.
- Invalid YAML makes the sheet read-only with a visible error. The app
  never overwrites a block it could not parse.
- Hand-written notes in the vault that are not app-owned are parsed by
  headings and tables and degrade to name, aliases, image and first
  paragraph. Nothing is invented.
- Players see a public card (name, image, concept, summary); the full
  sheet goes only to the owner and the narrator.

## Consequences

- The sheet is readable and editable in Obsidian without the panel, and
  the ladder can change per campaign without touching stored files.
- Renaming a label is a remove plus an add for the merge, which is why
  identity is the label and not the list position.
- The app displays mechanics but never computes them: no automatic stress
  or consequence arithmetic, no refresh recalculation from stunts.
- The format has no version field. Unknown keys are preserved instead,
  which keeps old files readable but means structural changes need a
  real migration when they come.
- A character-sheet pair is two files with two hashes, so one can be in
  conflict while the other is fine.
- The dice log and the campaign config are separate concerns; a roll
  never reads the vault, so it works while the vault is down.
