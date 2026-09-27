# Product

<!-- impeccable:product-schema 1 -->

## Platform

web

## Users

The maintainer and their own Discord guild(s) are the primary users: the maintainer operates Harpi, guild members use its music, dice, and TTS features through Discord and the web panel. Self-hosters running Harpi for their own servers are a confirmed second audience, kept runnable by strangers as a real constraint (self-hosting first).

## Product Purpose

Harpi replaces a pile of separate Discord bots with one simpler thing: music playback, dice rolling, and TTS in a single bot, plus an HTMX web panel for controlling music, all served by one Quart process. Success means the guild gets those features without juggling multiple bots and dashboards, and a self-hoster can run the whole thing from a repo clone.

## Positioning

One process, one panel. Music, dice, TTS, and an HTMX control panel share one runtime instead of a fleet of separate bots with separate dashboards. The bot and the panel are one feature on two surfaces (commands and panel), not two products.

## Operating Context

- Discord guilds: each guild has one `PlaybackSession` (playback state machine) tied to its voice connection.
- Music enters through yt-dlp search, stream selection and probing, FFmpeg decode, and mixing into the voice client.
- The web panel (HTMX/CRT retro theme) is served by the same process at `http://localhost:8000` in development; production runs via Docker Compose.
- Development: `uv` for Python deps, `make dev` for auto-reload, `make format` / `make check` as the verification gates.
- Tests are all fakes and all offline; the real bot must never be started to check something (it joins the maintainer's live guild).

## Capabilities and Constraints

- Features: music player (queue, layers, transport), dice roller, TTS using an external voice.
- Single Python 3.13 process running two event loops (Quart + discord.py); panel actions cross the loop boundary through `run_on_bot_loop`.
- Web surface renders HTML fragments for HTMX; pages are Quart blueprints plus HTMX action handlers in `pages/`.
- Hard product rules: music does not die while playing; bot state explains itself (physically in a voice channel means connected to it); no error requires a bot restart, and the bot alerts when failing, never failing in silence.
- `src/config.py` is the sole owner of environment configuration.
- The bot never imports from the web layer; `harpi_lib` holds domain logic with no discord.ui or Quart imports.

## Brand Commitments

- The CRT retro theme on the web panel is Harpi's identity and is binding: future design work must preserve it.
- Name: Harpi.
- Glossary vocabulary in `CONTEXT.md` is binding for code, docs, and discussion.

## Evidence on Hand

- `README.md` (feature list, run instructions).
- `CONTEXT.md` (domain glossary for both surfaces).
- `docs/agents/architecture.md`, `docs/agents/panel.md`, `docs/agents/testing.md`, `DESIGN.md`.
- `docs/adr/0002-perceptual-volume-slider.md`.
- No testimonials, case studies, press, or benchmarks exist; future work must not fabricate any.

## Product Principles

1. One process, one panel: a feature exists on the Discord command surface and the web panel as one thing, never as two products.
2. Simplicity over feature count: replacing other bots means fewer moving parts, not more features.
3. Never fail in silence: errors surface (persistent error region, bot alerts); no error may require a restart.
4. State must explain itself: what the bot reports matches what it is physically doing in voice.
5. Honest gates: verification runs offline against fakes; a failing gate is fixed or the dead thing is deleted, never faked or lowered.

## Accessibility & Inclusion

No product-specific accessibility requirement has been established. The CRT retro theme is binding, so future design work must reconcile readability with the theme rather than dropping it.
