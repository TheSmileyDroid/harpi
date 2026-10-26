# Harpi

This is a discord bot made mainly for replacing other bots
in a simplier way with features like:

- Music Player
- Dice Roller
- TTS using external voice

## Running

To run Harpi locally, install and upgrade the Python and web
dependencies in one step:

    make bootstrap

This runs `uv sync --upgrade` for the backend and `bun update` in `web/`
for the frontend. Run it again whenever you want to pull newer versions.

Build the frontend and run the bot:

    make build
    uv run python -m src

Or `make start`, which builds the SPA and runs the app. The panel is served
at http://localhost:8000 alongside the API.

For development with auto-reload:

    make dev

In development, Vite serves the UI at http://localhost:5173 with hot
module reload, and Quart serves the API at http://localhost:8000.

The panel signs in with Discord. Set `DISCORD_CLIENT_ID` and
`SECRET_KEY` in `.env` (copy `.env.example` to start) and register
`DISCORD_REDIRECT_URI` as a redirect on the Discord application. A guild
member authorizes the app at `GET /api/auth/discord` and gets a signed
session cookie; an account sharing no guild with the bot is refused. The
app binds to `127.0.0.1` by default; set `HOST` or pass `--host` to
change it.

To run in production, create the external edge network once and use Docker
Compose:

    docker network create harpi-edge
    docker compose up

The app publishes no host port. Nginx Proxy Manager reaches it as
`harpi-backend:8000` on `harpi-edge`; the network and the egress deny are
covered in [docs/security/runbook-edge-network.md](docs/security/runbook-edge-network.md).
