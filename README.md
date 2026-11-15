# Harpi

A Discord bot that replaces a pile of them: music player, dice roller and TTS,
with one Svelte panel for the music, all in one process.

## Run

```sh
make bootstrap   # uv sync --upgrade + bun update
make start       # builds the SPA, serves it and the API on :8000
make dev         # Vite on :5173 with reload, Quart on :8000
```

Sign-in uses Discord OAuth2. Copy `.env.example` to `.env`, set
`DISCORD_CLIENT_ID` and `SECRET_KEY`, and register `DISCORD_REDIRECT_URI` on the
Discord application. Only members of the guilds in `PANEL_GUILD_ALLOWLIST` are
admitted. The app binds `127.0.0.1` by default; set `HOST` or pass `--host`.

## Production

```sh
docker network create harpi-edge
docker compose up
```

No host port is published: Nginx Proxy Manager reaches `harpi-backend:8000` on
`harpi-edge`. See [docs/security/runbook.md](docs/security/runbook.md).

## Checks

`make check` runs every gate and prints one report; `make check-e2e` adds
Playwright; `make security` runs the scanners that are installed locally. See
[docs/agents/testing.md](docs/agents/testing.md) and
[docs/security/scanners.md](docs/security/scanners.md).
