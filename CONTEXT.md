# Harpi — Context & Glossary

This is the shared vocabulary for Harpi: a Discord bot that runs TTRPG
sessions, with a retro Tempad-styled web panel (Harpi Panel) to manage
music, TTS, and dice. Single-context repo — one `CONTEXT.md` at the root,
decisions recorded in `docs/adr/`.

Use these terms as defined here in issues, specs, commit messages, tests,
and docstrings. Don't drift to synonyms the glossary explicitly avoids.

## Glossary

- **Bot/Harpi** — the bot over Discord; the interface we use to communicate
  with Discord.
- **Harpi Panel / UI** — the web UI that contains options and presets for
  running games and playing music over the Discord interface.
- **Session** — all playback state and logic for a single guild. Everything
  a guild's audio needs lives behind one interface, so behaviour is
  predictable when the queue, volume, loop, layers, and TTS interact.
- **PlaybackSession** — the deep module that implements a session
  (`src/harpi_lib/audio/session.py`). It composes the voice client, the
  `AudioController`, and the `MixerSource` as internal seams — nothing
  outside the session touches them — and owns the mixer's end-of-track
  observer wiring. Its verbs are bot-loop-bound (async where they touch
  discord.py's voice APIs). Read model: `SessionStatus`.
- **SessionManager** — the registry and lifecycle for sessions
  (`src/harpi_lib/audio/session_manager.py`). One `PlaybackSession` per
  guild, created by `connect`, found by `get` / `ensure` (connect-if-
  missing), torn down by `disconnect`. An unexpected voice disconnect
  self-cleans through its `on_voice_state_update` handler so no ghost
  session lingers. This is the seam the cogs, routes, and tests cross.
- **SessionStatus** — the immutable read-model snapshot of a session
  (`guild_id`, `connected`, `is_playing`, `is_paused`). Every reader — the
  panel JSON, the HTMX fragments, the server status, the chat list command —
  consumes the same snapshot, so the panel and the chat always agree.
- **Threading contract** — the rule that the bot's event loop is the single
  writer for all session state. Session verbs must be awaited from the bot
  loop; the mixer's end-of-track observers fire from the voice-sending
  thread and must marshal work back onto the bot loop before mutating
  anything. The web panel crosses the loop only via the `run_on_bot_loop`
  bridge.

## Avoid

- **state bag / GuildConfig** — the former mutable per-guild state that the
  session replaces. Don't use it to mean a session.
