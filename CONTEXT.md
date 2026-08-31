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

### Structure

**Bot state**:
The handle to the running bot (`src/bot_state.py`). The panel reads it, the bootstrap writes it. The bot never imports from the web layer.

**Cog**:
A discord.py command module in `src/cogs/`. Commands stay thin: parse, delegate, format.

**Page**:
A web surface in `pages/`: a Quart blueprint plus its HTMX action handlers.
