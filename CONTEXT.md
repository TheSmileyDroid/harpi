# Harpi

A Discord bot (music, dice, TTS) and an HTMX web panel sharing one process and one runtime. This glossary is the shared vocabulary for both surfaces; when code, docs, or discussion name a concept here, use this term.

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

**Transport**:
The fixed bottom bar of the Music page: progress bar, play/pause, skip/previous, loop, volume. The Session's controls, rendered as one surface.
_Avoid_: player (reserved), playback bar, control bar

**Search results**:
The transient list of candidates returned by the single search on the Music page, shown as an overlay dropdown. Ephemeral by design: they live in the page, not in the Session, and vanish on close or navigation.
_Avoid_: search panel (there is only one search), results page

**Side panel**:
The right-hand column of the Music page holding the Queue and Layers as tabs. One panel, two views.
_Avoid_: queue panel, layers panel (those are the tabs)

**Toast**:
A transient amber confirmation that fades on its own (action succeeded). The opposite of the persistent error region: errors stay until resolved, toasts die quietly. Toasts are never green.
_Avoid_: notification, alert (alert is red and means error)

### Structure

**Bot state**:
The handle to the running bot (`src/bot_state.py`). The panel reads it, the bootstrap writes it. The bot never imports from the web layer.

**Cog**:
A discord.py command module in `src/cogs/`. Commands stay thin: parse, delegate, format.

**Page**:
A web surface in `pages/`: a Quart blueprint plus its HTMX action handlers.

**Design review**:
The mandatory pass that judges panel work against the design language (`docs/agents/design.md`). Split by checkability: rules a test can verify are tested (TDD); rules only pixels can reveal go to the vision reviewer. Runs before-done and after big layout changes.
_Avoid_: checker, verifier, audit (Probe is the audio pre-flight, not this)

**Verdict**:
The structured output of a Design review: one entry per checklist item — pass, fail, or inapplicable — with evidence. A stale or missing Verdict fails the gate; a Verdict never overrides a failing test.
