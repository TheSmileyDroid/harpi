# Architecture, glossary, code layout

## One process, two event loops

Quart and discord.py share one process and two event loops. The panel renders HTML fragments for HTMX. Actions post to `pages/`, resolve the guild's `PlaybackSession`, and cross the loop boundary through `run_on_bot_loop` — never call a bot-loop coroutine directly from panel code. Music enters as a yt-dlp search, gets a stream picked and probed for playability, decodes through FFmpeg, and mixes with any layers into the voice client. `src/config.py` is the only place that reads the environment.

## Glossary

- **session** is one guild's playback state machine (`PlaybackSession`). There is one per voice connection.
- **layer** is background audio playing over the queue (tones, TTS). The mixer sums layers with the queue source.
- **cog** is a discord.py command module in `src/cogs/`. Commands stay thin: parse, delegate, format.
- **page** is a web surface in `pages/`: a Quart blueprint plus its HTMX action handlers.
- **bot state** (`src/bot_state.py`) is the handle to the running bot. The panel reads it, the bootstrap writes it. The bot never imports from the web layer.
- **source chain** is how music plays: yt-dlp search, stream selection and probing (`ytdl_source`, `stream_probe`), FFmpeg decode (`ffmpeg_source`), mixer, voice client.

## Where code lives

- `src/cogs/` - Discord commands. Thin handlers over session methods.
- `src/harpi_lib/` - domain logic: `audio/` (session, mixer, sources), `music/` (yt-dlp, probing, ffmpeg), `math/` (dice parser). No discord.ui or Quart imports.
- `src/bot_state.py` - the running-bot handle and the loop bridge.
- `src/config.py` - `Settings`, sole owner of `os.getenv`.
- `pages/` - web blueprints, HTMX actions, the guilds lookup.
- `app.py` - app assembly, template filters, the panel's startup hook.
- `templates/` - Jinja + HTMX, djlint and prettier format it.
- `tools/crap_check.py` - the CRAP gate itself.
- `tests/` - tests, all fakes, all offline.
