# Product

## Platform

web

## Users and purpose

The maintainer and their guilds run Harpi; members use its music, dice and TTS
through Discord and the panel. Self-hosters are a confirmed second audience: a
stranger must be able to run it from a repo clone. One bot instead of a pile:
music, dice and TTS, plus a Svelte panel for the music, in one Quart process.

## Positioning

One process, one panel. The bot and the panel are one feature on two surfaces,
never two products.

## Operating context

- One `PlaybackSession` per guild, tied to its voice connection.
- Music: yt-dlp search, stream selection and probing, FFmpeg decode, mixing.
- The panel is served by the same process; `make start`, or Compose in prod.
- Dev: `uv`, `make dev` for reload, `make format`/`make check` as the gates.
- Tests are offline fakes; the real bot is never started to check something.
- One Python process, two event loops; panel actions cross through
  `run_on_bot_loop`. `src/config.py` is the sole owner of the environment. The
  bot never imports the web layer; `harpi_lib` imports neither discord.ui nor
  Quart.

## Capabilities and hard rules

- Music (queue, layers, transport), dice, TTS.
- The panel shows who is linked to the selected guild and the last connect or
  disconnect; the SQLite registry (ADR 0008) persists it.
- Music does not die while playing; state explains itself; no error needs a
  restart; failures alert instead of staying silent.

## Brand

The retrofuturist industrial-placard identity is binding; see `DESIGN.md`. It
replaced the unmarked-carrier receiver world; future design extends it, never
replaces it. The name is Harpi; the glossary in `docs/agents/architecture.md`
is binding. No testimonials, benchmarks or press exist; do not fabricate any.

## Principles

1. One process, one panel: a feature exists on both surfaces as one thing.
2. Simplicity over feature count.
3. Never fail in silence.
4. State must explain itself.
5. Honest gates: verification runs offline against fakes; a failing gate is
   fixed or the dead thing deleted, never faked or lowered.

No product-specific accessibility requirement is established. The theme is
binding, so readability is reconciled with it rather than dropped.
