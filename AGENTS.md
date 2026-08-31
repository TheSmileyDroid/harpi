# Harpi

Harpi is a Discord bot (music, dice, TTS) and an HTMX web panel, served by Quart in the same process. Python 3.13, uv, pytest.

One process runs two things: the Discord bot and the panel. They share one runtime and one set of quality gates.

## The things we never compromise

- music should not die while playing
- the bot state should explain itself. If it is physically in a voice channel it means it is connected to the voice channel.
- no error should need to restart the bot.

## A note from TheSmileyDroid/SmileyDroid/Sorriso

I like simplicity and abstraction, but I also like to test great and new ambitious ideas. I would make the wheel again if it would make it better. This repo is one of my special creations, it should be something of a State of the Art. This bot should always be available when needed and should always alert when it is failing. Do not fail in silence.

## A small glossary

- **you** is the agent reading this file and changing Harpi.
- **we, us** is TheSmileyDroid and the people building Harpi. These are who you are talking to now.
- **session** is one guild's playback state machine (`PlaybackSession`). There is one per voice connection.
- **layer** is background audio playing over the queue (tones, TTS). The mixer sums layers with the queue source.
- **cog** is a discord.py command module in `src/cogs/`. Commands stay thin: parse, delegate, format.
- **page** is a web surface in `pages/`: a Quart blueprint plus its HTMX action handlers.
- **bot state** (`src/bot_state.py`) is the handle to the running bot. The panel reads it, the bootstrap writes it. The bot never imports from the web layer.
- **source chain** is how music plays: yt-dlp search, stream selection and probing (`ytdl_source`, `stream_probe`), FFmpeg decode (`ffmpeg_source`), mixer, voice client.

## The ways to hurt yourself

1. **Committing secrets.** `.env` holds the real Discord token, `cookies.txt` holds YouTube credentials. Both are gitignored, keep them that way. If you ever need values from `.env` for a test, hardcode a fake, not the real one.
2. **Testing against the real guild.** `make start` connects to the maintainer's actual Discord server and voice channels. Tests use fakes and never touch the network. Do not start the bot to "check" something. Write the test or run `make check`.
3. **Faking a gate.** The gates in `make check` are the contract. When one fails, fix the cause or delete the dead thing it found. Lowering a threshold, adding an ignore, or writing a test that asserts nothing to make it pass are all worse than leaving it red and saying so.

## Hit every surface

A behavior usually exists on two surfaces: Discord commands and the panel. Fixing one is not fixing the feature. Before calling music work done, walk this list:

- **Surfaces.** play, pause, skip, seek, queue and layers are reachable from both a `MusicCog` command and a `pages/music.py` action. If you added one, check the other.
- **Reverse states.** If you added a way in, add the way out. Connect needs disconnect. Loop on needs loop off. A one-way door is a bug.
- **Both loops.** The bot and Quart run on different event loops. Panel code that touches discord.py internals goes through `run_on_bot_loop`, never calls the coroutine directly.
- **Templates.** Panel behavior lives next to its markup (LoB): the block the HTMX request targets, the handler that serves it, in `pages/` and `templates/pages/` together.
- **Panel patterns.** Before writing fragment handlers, `hx-*` attributes, polling, or panel scripting, read `.pi/skills/htmx-panel/SKILL.md`: the official htmx essay patterns mapped to this stack, plus the known debt list.

## Verifying

- `make format` then `make check`. That is the whole gate: ruff, ty, djlint, pytest with coverage, the CRAP gate, copy-paste detection, prettier, vulture. One command, exit 0 means done.
- Backend behavior changes ship with focused tests for that behavior. Tests are deterministic: no network, no sleeps. A test that needs a timeout to pass is wrong.
- The CRAP gate fails any function whose complexity times its missing coverage exceeds 8 (the bar for AI-written code; the human bar is 6). Complex code needs tests, tested code stays simple. Both count.
- Touching core audio or dice logic: also run `make mutants` and triage the survivors before calling it done.
- Agents run `make check` before claiming work is done.

## How it works

Quart and discord.py share one process and two event loops. The panel renders HTML fragments for HTMX. Actions post to `pages/`, resolve the guild's `PlaybackSession`, and cross the loop boundary through `run_on_bot_loop`. Music enters as a yt-dlp search, gets a stream picked and probed for playability, decodes through FFmpeg, and mixes with any layers into the voice client. `src/config.py` is the only place that reads the environment.

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

## Agent skills

### Issue tracker

Issues live as local markdown under `.scratch/<feature-slug>/` in this repo. See `docs/agents/issue-tracker.md`.

### Triage labels

Default vocabulary: `needs-triage`, `needs-info`, `ready-for-agent`, `ready-for-human`, `wontfix`. See `docs/agents/triage-labels.md`.

### Domain docs

Single-context: `CONTEXT.md` + `docs/adr/` at the repo root. See `docs/agents/domain.md`.

## Taste

- The name is the documentation. If a name does not explain, fix the name.
- Templates over copied code. The copy-paste gate means it.
- An invariant lives in the name, not in a comment.
- A comment references a doc or explains a why. It never narrates the how. Docstrings that render real documentation (command help, API contracts) stay.
- The behavior of a unit of code should be visible from that unit: an HTMX block names its target, a page keeps its actions near.
- Do not preserve complexity because it exists. Do not add machinery because it looks impressive. Find the real constraint, then build the smallest thing that makes correct behavior obvious.
- Do not use mocks, use fakes instead.
- If a rule here fights the task in front of you, say so loudly and get a human sign-off before breaking it.
