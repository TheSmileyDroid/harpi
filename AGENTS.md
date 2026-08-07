# Harpi

Harpi is a Discord bot for running TTRPG sessions — music, TTS, dice, and a
web panel to manage them. The UI (the Harpi Panel) is HTMX with a retro
CRT/Tempad theme; the backend is Python 3.13/uv on Quart, discord.py, yt-dlp.

## Agent skills

### Issue tracker

Issues and specs live in this repo's GitHub Issues, operated via the `gh` CLI. See `docs/agents/issue-tracker.md`.

### Triage labels

The five canonical triage roles use their default label names. See `docs/agents/triage-labels.md`.

### Domain docs

Single-context: one `CONTEXT.md` and `docs/adr/` at the repo root. See `docs/agents/domain.md`.

## Some thoughts from the author (SmileyDroid/Sorriso/Gabriel)

This is a big project. I wouldn't want to say it is finished so soon. I
think it has a lot of potential to be an amazing alternative to other
Virtual Tabletops (VTTs). A free and open-source alternative that gives you
the possibility of playing with your friends over any discord server. Even
if normally other VTTs have maps and are built for strategy or dungeon crawl
games, this project focuses on the narrative feel of RPG games and it means
that we do not use maps because usually we focus on the imagination of the
players over the scene. However, to do this, we need that all the other
aspects of the game have a complete experience, from the music and the most
of techniques to playing sounds to an easy character sheet management and
dice rolls.

This is a project different from anything I have already seen. So do not go
with the flow of existing solutions. Explore ideas.

Quick glossary:

- Bot/Harpi: the bot over Discord, the interface we use to communicate with Discord.
- UI/Harpi Panel: the web UI that contains options and presets for running games and playing music over the Discord interface.
- me: SmileyDroid or Sorriso or Gabriel. The creator of this bot.

### Style

The style of UI and features should follow a retro aesthetic based on old
computers, featuring yellowish lighting that follows the style of TVA's
*Tempad*.

### Don't be afraid

When planning, do not be afraid to suggest seemingly insane solutions. For
example, rewriting an entire discord lib from scratch to be able to do
things unseen before. Seems insane, but it's absolutely doable with modern
tools.

You can add more libs along the way, but libs that are so simple that don't
have a lot of users could be implemented on the project.

### Fight for the "obvious" solution

We should avoid being clever and doing things because they seem smart. We
want everything we build to be so obvious it feels kind of stupid.

When one of us prompts you, never hesitate to push back and suggest ways we
could make things more obvious. Note that "simple" and "obvious" are not
always aligned, sometimes the "obvious" solution is more complex.

## Some general rules

- When making a new feature, make tests for it.
- Always use `make check` at the root to check for lint, format, type, vulture errors.
- Use modern tools like uv.
- Write in plain text; emojis break immersion. If a glyph is needed, let the theme render it.
