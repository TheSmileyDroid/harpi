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
The collapsible right-hand column of the Music page (15.5rem, above 56rem) holding the Layers, the Session readouts and the Linked roster. The Queue lives in the main column under Now Playing.
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
