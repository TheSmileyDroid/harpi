# Harpi

A Discord bot (music, dice, TTS) and a Svelte web panel sharing one process and one runtime. This glossary is the shared vocabulary for both surfaces; when code, docs, or discussion name a concept here, use this term.

## Language

### Playback

**Session**:
One guild's playback state machine (`PlaybackSession`). There is exactly one per voice connection.
_Avoid_: player, guild player, audio session

**Session manager**:
One per bot; owns the map from guild to its Session and creates or destroys Sessions as voice connections change (`SessionManager`).
_Avoid_: session registry, controller (use for the Audio controller)

**Audio controller**:
The source-collection owner inside one Session: holds the current queue source, layers, and TTS track, and cleans sources up (`AudioController`).
_Avoid_: mixer (the Mixer is a different thing), queue

**Mixer**:
Sums the Session's layers with the queue source into one audio stream for the voice client.

**Layer**:
Background audio playing over the queue (tones, TTS). Layers are summed by the Mixer.

**Source chain**:
How music plays: yt-dlp search → stream selection and probing → FFmpeg decode → Mixer → voice client.

**Probe**:
A short FFmpeg pre-flight that confirms a stream URL actually decodes audio (with retries and a time budget) before playback commits to it. Probe failure means the source is rejected, not that playback dies.
_Avoid_: check, validate, ping

**JS challenge runtime**:
The external JavaScript engine (deno, node, bun, or quickjs) that solves YouTube's challenge scripts on yt-dlp's behalf. A missing runtime is the difference between a playable and an unplayable track (ADR 0005).
_Avoid_: JS engine, node, deno (those name instances, not the role)

**Cookie file**:
The master logged-in YouTube cookie set (`cookies.txt`) used for extraction. It is input only: yt-dlp reads a copy and any edit it makes is kept as a backup (ADR 0006).
_Avoid_: cookie jar, session store

**Transport**:
The fixed bottom bar of the Music page: progress bar, play/pause, skip/previous, loop, volume. The Session's controls, rendered as one surface.
_Avoid_: player (reserved), playback bar, control bar

**Volume**:
Linear gain applied to a source, 0.0–1.0, where 1.0 is unity: the ceiling never amplifies above the source. Volume is what is stored, what the `!volume` command speaks, and what the readout shows; the panel slider is a perceptual input device over it (position squared, ADR 0002).
_Avoid_: loudness (perception, not the value), level

**Search results**:
The transient list of candidates returned by the single search on the Music page, shown in the search palette (a modal dialog). Ephemeral by design: they live in the page, not in the Session, and vanish on close or navigation.
_Avoid_: search panel (there is only one search), results page

**Layers rail**:
The collapsible right-hand column of the Music page (15.5rem, above 56rem) holding the Layers, the Session readouts and the Linked list. The Queue lives in the main column under Now Playing.
_Avoid_: side panel, queue panel, layers panel

**Toast**:
A transient amber confirmation that fades on its own (action succeeded). The opposite of the persistent error region: errors stay until resolved, toasts die quietly. Toasts are never green.
_Avoid_: notification, alert (alert is red and means error)

### Structure

**Bot state**:
The handle to the running bot (`src/bot_state.py`). The panel reads it, the bootstrap writes it. The bot never imports from the web layer.

**Viewer**:
A signed-in panel user with a selected guild and channel, refreshed by the presence sample every five seconds. A viewer goes stale after 15 seconds without one.
_Avoid_: user (the Discord account), session (that is playback)

**Link**:
The panel's connection to the server's event stream: linking, live, or reconnecting. The Output picker shows it as LINKING, LINK LIVE, or LINK LOST.
_Avoid_: connection (that is voice), socket

**Stale**:
A panel reading state: values stopped arriving while the link may still be up. Shown as an amber STALE tag in the top bar, with the readouts dimmed. Recovery clears it, and nothing is lost by waiting.
_Avoid_: disconnected (that is the link), offline (that is the bot)

**Directory**:
The guilds the bot is in, plus the voice channels of the selected guild. It travels as its own frame, and only when it changes.
_Avoid_: guild list, channel list (those are the API endpoints)

### Live updates

**Sampler**:
One per guild, owned by the panel process. It samples the guild's Session and the Directory on a fixed cadence and hands changed frames to every open stream, so viewers share one poll instead of each running their own.
_Avoid_: poller, watcher, broadcaster

**Status frame**:
The full snapshot a stream sends when anything except the playback position changes. It is the only frame that replaces the whole panel state.
_Avoid_: status push, update, sync (the noun is the sampler's job)

**Position frame**:
A small frame carrying only the playback position, sent every few seconds while a stream is open and immediately when the position jumps. The panel advances the readout between frames from the last sample.
_Avoid_: progress event, tick

**Heartbeat**:
An empty named frame sent every few seconds while a stream is open. Its arrival alone proves the link alive, even when the sampler has nothing to say.
_Avoid_: ping, keepalive

**Registry**:
The SQLite store of viewers and connect/disconnect events (`src/storage/`, ADR 0008). The panel reads presence from it; the API records selections and connection events.
_Avoid_: database (the file), cache, store (the Svelte store)

**Cog**:
A discord.py command module in `src/cogs/`. Commands stay thin: parse, delegate, format.

**Page**:
A web surface in `pages/`: a Quart blueprint answering JSON or the SSE stream.

**Contract**:
The panel's wire shape. Pydantic models in `src/panel/schemas.py` are the single source of truth, and `make contract` generates the OpenAPI document, the client TypeScript types and zod validators, and the test fixtures into `web/src/lib/contract/`. Both halves validate against it, and `make check` fails on drift.
_Avoid_: API spec, types file

**Design language**:
How the panel looks and behaves (`DESIGN.md`). Mechanically checkable rules live in `tests/test_design_language.py`; the rest is judgment applied while editing.
_Avoid_: design review, verdict (the gate is gone)

### Identity

**Snowflake**:
A 64-bit Discord entity identifier (guild, channel, user, message). Harpi treats one as an opaque label, never as a quantity.
_Avoid_: ID, Discord ID, entity id

### Campaigns and content

**Campaign**:
A play group bound to one Discord guild, with a narrator, members and one content source. The slug is immutable and appears in three places: the vault folder, the `harpi-campaign` block and SQLite.
_Avoid_: guild (one guild can hold several campaigns), game, table (the live session)

**Content source**:
Where a campaign's sheets live: `vault` (notes under `Harpi/Campaigns/<slug>/`) or `local` (SQLite, M2). The M1 ships `vault` only.
_Avoid_: backend, storage, provider

**Atlas**:
The authored world map of nested maps, kept as an Obsidian Canvas. Read-only viewer in M2, editor in M3. It is not the map of a Table.
_Avoid_: world map, overworld, campaign map

### Characters and sheets

**Character**:
The identity and lore note of a person in the fiction (`tipo: personagem`), with a stable `chr_` id when the app creates it. Lore belongs to the campaign and has no owner.
_Avoid_: sheet (the playable state), token (the piece on the map), NPC (a role)

**Sheet**:
The playable state of one Character: a note with a fenced `harpi-sheet` block, two prose sections, an owner and a status. A Character has at most one pending or active Sheet. UI: Ficha.
_Avoid_: character, card, mechanics sheet

**PC**:
A Character whose Sheet is owned by a player.

**NPC**:
Every Character that is not a PC. Created by the narrator, starts active, and becomes visible to players when revealed.

**Public card**:
What a player sees of someone else's character: name, portrait, concept and summary. The sheet never leaves the server for anyone but its owner and the narrator.
_Avoid_: preview, profile, summary view

**Revealed character**:
An NPC that entered the visible cast, by narrator action or by its first token landing in a revealed zone. It stays in the cast after its token leaves the scene.
_Avoid_: discovered, unlocked, visible

**Sheet conflict**:
The same field changed in the panel and in the vault since the last version the app accepted. The file stays untouched and the sheet turns read-only until each field gets a decision. A sheet is `ok`, `conflito`, `ausente`, `invalido` or `desconhecido`.
_Avoid_: merge error, divergence, dirty

### Table

**Table**:
One live session of the tabletop: a campaign's scene, tokens, fog and turns, bound to one text channel. Only one is open per campaign and per channel. UI: Mesa.
_Avoid_: session (that is playback), room, game

**Scene**:
A prepared map: image or drawing, grid, named zones and initial fog, authored under `scenes/` and loaded into a Table.
_Avoid_: map (UI word for the rendered scene), encounter, level

**Scene source**:
Where a scene's image comes from: `image` (a vault image or an uploaded asset) or `sketch` (rooms drawn in the editor and saved as an SVG in the campaign's assets). UI: Origem da cena.
_Avoid_: mode, type, style

**Scene blueprint**:
The authored scene file under `scenes/`, with image, grid, zones and initial fog, and no tokens.
_Avoid_: template, definition

**Table snapshot**:
The periodic copy of live table state under `tables/`: current scene with fog, tokens, round and turn. A safety net for database loss, never a second source of truth.
_Avoid_: save, backup state, persistence file

**Zone**:
A named area of a scene: a union of whole-cell rectangles revealed or hidden as one. In a drawn scene a room (*sala*) is a zone, so the drawn rooms are the map and the fog at once. UI: área (gallery, summaries), sala (drawing).
_Avoid_: room (only for sketch), rect, mask

**Fog**:
The reveal state of a table: which zones are revealed, and whether the area outside every zone is hidden. Hidden zones are not drawn for players. A game aid, not a security boundary.
_Avoid_: mask, shadow, visibility, darkness

**Token**:
A piece on the map bound to a Table and a scene: position in cells, size, label, optional owner and Character, color and visibility. Its portrait comes from the linked Character.
_Avoid_: miniature, piece, actor, marker

**Public token**:
A token a player can see: `visible: true`, and either its center falls in a revealed zone or `fog_outside` is off and it sits outside every zone. Only public tokens take part in a round.
_Avoid_: visible token (that is one field), revealed token

**Turn**:
The span in which one token acts during the current round. At most one is open per Table.
_Avoid_: initiative, order, activation

**Round**:
One pass over the public tokens of the current scene. It closes when the last token that has not acted ends a turn, and the narrator opens the next.
_Avoid_: cycle, initiative round, pending (that is a member role)

**Table stream**:
The SSE connection a viewer opens to one Table.
_Avoid_: socket, channel, feed

**Table presence**:
The list of people with the table stream open right now, with display name and role (`table.viewers`), held in memory by the broadcaster. Never a snowflake. Not the panel **Viewer**: this one is per Table. UI: Na mesa.
_Avoid_: roster, viewers (the panel concept), presence list

**Stream revision**:
The per-Table counter `stream_rev`, incremented once per accepted change, kept in memory and never persisted. Separate from the per-row revisions used for conflict checks.
_Avoid_: version, rev (the row revs)

**Table frame**:
`table.snapshot` or `table.delta`: the state of the scene as it travels to the client.
_Avoid_: update, payload, tick

**Token move**:
An accepted position change, sent at most 10 times per second per Table. The last drop wins.
_Avoid_: drag event, position, delta

**Drag marker**:
The ephemeral notice that someone is dragging a token, renewed by each accepted move and gone 3 s after the last one. It never blocks anyone.
_Avoid_: lock, claim, selection

**Roll**:
One accepted evaluation of a dice expression in an open Table: a row in `rolls` with the text frozen as the parser printed it.
_Avoid_: dice result, check, throw

**Roll message**:
The Discord message that carries a roll: the author's message in the channel, the bot's message from the panel.
_Avoid_: post, embed

**Dice log**:
The rolls of one Table ordered by `(created_at, id)`. Kept in SQLite only and recovered from the API, never from the table snapshot.
_Avoid_: history, feed

### Access

**Narrator**:
The campaign owner (`campaigns.narrator_id`), who approves sheets, prepares scenes and runs the table. UI: Narrador.
_Avoid_: GM, DM, master, owner (ambiguous with the sheet owner)

**Player**:
A campaign member with an `ativo` Sheet. UI: Jogador.
_Avoid_: user, member (any row in `members`), participant (a token)

**Pending**:
A campaign member with no `ativo` Sheet. UI: Pendente. Distinct from a pending sheet, which is a file status.
_Avoid_: waiting, applicant

**Spectator**:
A signed-in user from an allowed guild, outside the campaign, who watches one Table with the spectator flag on, with no sheet access. UI: Espectador.
_Avoid_: guest, anonymous, visitor

**Sheet owner**:
The Discord snowflake in `harpi-owner`: the truth of who plays a sheet. UI: Dono da ficha.
_Avoid_: owner (that is the narrator), player (a role derived from the sheet)

**Table access**:
The condition that opens a table's stream, map and summary: campaign membership (the narrator included), or a spectator on a table with the flag on.
_Avoid_: permission, grant
