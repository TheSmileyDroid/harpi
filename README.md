# Harpi

This is a discord bot made mainly for replacing other bots
in a simplier way with features like:

- Music Player
- Dice Roller
- TTS using external voice

## Running

To run Harpi locally you will need to install the dependencies from
the pyproject into your virtual environment. Use the `uv` package
manager:

    uv sync

Then run the bot:

    uv run python -m src

For development with auto-reload:

    make dev

The web UI (HTMX/CRT retro theme) is served directly by the backend
at http://localhost:8000.

To run in production, use Docker Compose:

    docker compose up


