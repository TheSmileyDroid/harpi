# Discord OAuth panel authentication

## Problem

The panel authenticates with a shared `PANEL_TOKEN` exchanged at
`POST /api/session` for a session cookie. A shared secret says nothing
about who is on the other end and has to be passed around by hand.

## Goal

Sign in with Discord. A guild member opens the panel, authorizes the
Harpi Discord application, and gets a panel session bound to their
Discord account. Nobody else gets in.

## Decisions

- **Discord OAuth only.** The panel token path is removed, not kept as a
  fallback. One way in.
- **Members of a guild the bot is already in** may enter. A Discord
  account that shares no guild with the bot is denied.
- **Authorization code grant with PKCE (S256), public client.** No
  client secret is stored. Discord advertises `S256` in its discovery
  document and accepts the `none` token auth method; a token exchange
  with `client_id` in the body and no secret answers `invalid_grant`
  (bad code), not `invalid_client`, which proves the flow.
- **Scopes**: `identify` and `guilds`.

## Discord application

- Application: SmileyBot (`891732797054681119`), reused as the OAuth2 app.
- Redirect URI registered: `http://localhost:8000/api/auth/discord/callback`
  (`DISCORD_REDIRECT_URI` overrides it for another host).

## Configuration

- `DISCORD_CLIENT_ID` — the application (client) id.
- `DISCORD_REDIRECT_URI` — default `http://localhost:8000/api/auth/discord/callback`.
- `PANEL_TOKEN` — removed.

## Routes

- `GET /api/auth/discord` (public) — mints a state and a PKCE verifier,
  stores both in the session, redirects to Discord's authorize URL.
- `GET /api/auth/discord/callback` (public) — validates state and the
  RFC 9207 `iss`, exchanges the code, reads the user and their guilds
  (paginated, so no 200-guild cap), compares against every guild the bot
  is in (fetched uncapped), sets `session["authenticated"]`, `user_id`,
  `username`, `permanent`, then redirects to `/`. Failures redirect to
  `/?auth=<reason>`: `unconfigured`, `cancelled`, `failed`, `unavailable`
  (the bot could not answer), `denied` (no shared guild).
- `POST /api/logout` (public) — clears the session, answers
  `{"authenticated": false}`.
- `GET /api/session` (guarded) — the session probe, unchanged.
- `POST /api/session` — removed.

## Panel

- `SignIn.svelte` shows a single "Continue with Discord" button that
  navigates to `/api/auth/discord`.
- `+page.svelte` reads `?auth=` on boot and reports the reason.
- The topbar carries a sign-out control calling `POST /api/logout`.

## Files

- `src/config.py` — add the two settings, drop `panel_token`.
- `src/discord_oauth.py` — new: PKCE, authorize URL, token exchange,
  user, guilds (aiohttp, no Quart).
- `pages/auth.py` — new blueprint.
- `pages/api.py` — drop the token exchange, keep the session probe.
- `app.py` — register the blueprint, extend `PUBLIC_API_ROUTES`.
- `src/panel/schemas.py` — drop `SessionRequest`.
- `web/` — `SignIn.svelte`, `+page.svelte`, `StatusSurface.svelte`,
  `api.ts`; regenerate the contract.
- `docs/adr/0007-discord-oauth-panel-authentication.md` — the decision.
- Tests: pytest for the flow with a faked Discord; Vitest and Playwright
  updated for the button.
