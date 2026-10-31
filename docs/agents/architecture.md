# Architecture, glossary, code layout

## One process, two event loops

Quart and discord.py share one process and two event loops. The panel is a Svelte single-page app served as static assets by Quart, which exposes a session-guarded JSON API and an SSE status stream. API handlers in `pages/` resolve the guild's `PlaybackSession` and cross the loop boundary through `run_on_bot_loop` — never call a bot-loop coroutine directly from panel code. Music enters as a yt-dlp search, gets a stream picked and probed for playability, decodes through FFmpeg, and mixes with any layers into the voice client. One SQLite file behind `src/storage/` holds the panel registry: each viewer's selection and heartbeat, and the connect/disconnect events. `src/config.py` is the only place that reads the environment.

## Glossary

- **session** is one guild's playback state machine (`PlaybackSession`). There is one per voice connection.
- **layer** is background audio playing over the queue (tones, TTS). The mixer sums layers with the queue source.
- **cog** is a discord.py command module in `src/cogs/`. Commands stay thin: parse, delegate, format.
- **page** is a web surface in `pages/`: a Quart blueprint answering JSON or the SSE stream.
- **bot state** (`src/bot_state.py`) is the handle to the running bot. The panel reads it, the bootstrap writes it. The bot never imports from the web layer.
- **sampler** (`src/panel/sampler.py`) is one per-guild poll shared by every open stream. It owns the values and the failure boundary; the stream frames them on its own tick (ADR 0009).
- **source chain** is how music plays: yt-dlp search, stream selection and probing (`ytdl_source`, `stream_probe`), FFmpeg decode (`ffmpeg_source`), mixer, voice client.

## Where code lives

- `src/cogs/` - Discord commands. Thin handlers over session methods.
- `src/harpi_lib/` - domain logic: `audio/` (session, mixer, sources), `music/` (yt-dlp, probing, ffmpeg, `source_policy` for the URL decision, `ytdl_options` for the public-mode options), `math/` (dice parser). No discord.ui or Quart imports.
- `src/panel/` - the domain seam the API and the bot share: `state`, `actions`, `serialization`, `sampler` (one per-guild poll shared by every open stream, ADR 0009), `schemas` (the Pydantic wire models that are the panel contract, ADR 0004), `campaigns` (the campaign access resolver, ADR 0013), `vault` (the vault root read once at boot), `vault_index` (the in-memory vault file and note index, rebuilt at boot and by the 60 s scan), `notes` (frontmatter and prose parsing for vault notes), `cast` (the campaign roster and public cards one role may see), `login` (cookie name, lifetime, and freshness), `rate_limit` (token buckets and stream slots), `retention` (the daily purge of presence rows past the retention window), `backup` (the daily registry backup and its restore check), and `disk_pressure` (the periodic data-volume check).
- `src/storage/` - the panel registry: SQLite database, ordered migrations, the `Registry` seam (ADR 0008), and the campaign seed.
- `src/alerts.py` - the operator alert dispatcher, its webhook sender, and the SSE growth threshold.
- `src/logging_setup.py` - the loguru sinks both entry points install: stdout, the rotated log, the separate security log, and the redaction wiring.
- `src/redaction.py` - the pure secret scrubber and its loguru patcher.
- `src/security_log.py` - the one-line security records, the request classifier behind them, and the response-status alert classifier.
- `src/bot_state.py` - the running-bot handle and the loop bridge.
- `src/config.py` - `Settings`, sole owner of `os.getenv`.
- `pages/` - web blueprints: the JSON API, the campaign routes, the SSE stream, and the request guard the VTT blueprints share.
- `app.py` - app assembly, the SPA asset routes, the panel's startup hook.
- `web/` - the SvelteKit SPA (Vite build, API client, SSE client).
- `tools/` - the offline gates (`crap_check`), the contract export, the registry backup CLI (`backup_db`), and the release gate helpers (`release_gate`).
- `deploy/` - operator tooling: the edge-network egress rules, the NPM proxy host and rate-limit config, fail2ban jails, and the release-gate and verification scripts.
- `tests/` - tests, all fakes, all offline.
