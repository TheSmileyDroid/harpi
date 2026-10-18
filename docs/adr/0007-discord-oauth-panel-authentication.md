# Sign the panel in with Discord, not a shared token

The panel was gated by a shared `PANEL_TOKEN` exchanged once at `POST /api/session` for a signed cookie. A shared secret identifies no one: it cannot say who is on the other end, it must be copied by hand to every person who should reach the panel, and rotating it locks everyone out at once. Harpi already knows its audience through Discord, so the panel now authenticates with Discord OAuth2 and admits only accounts that share at least one guild with the bot. The flow is the authorization code grant with PKCE (S256) as a public client, so no client secret is stored and none has to be rotated. A guild the bot is not in grants nothing, which keeps the panel scoped to the same servers the bot already serves.

## Considered options

- **Keep the token as a fallback**: rejected. Two ways in means the weaker one is the real floor, and a self-hoster who never registers an OAuth app still has a shared secret to leak.
- **Authorization code grant with a client secret**: rejected in favor of PKCE. Discord advertises `S256` in its discovery document and accepts the `none` token auth method (a token exchange carrying `client_id` and no secret answers `invalid_grant`, not `invalid_client`), so the secret adds a stored credential and a rotation duty with no gain.
- **Allow any Discord account**: rejected. The panel drives playback in the bot's guilds; an account in none of them has nothing to control.
- **Restrict to the bot owner only**: rejected. The maintainer's guild members are confirmed users of the music features, not just the maintainer.

## Consequences

- `DISCORD_CLIENT_ID` replaces `PANEL_TOKEN`; `DISCORD_REDIRECT_URI` must be registered on the Discord application and match exactly.
- The bot must be running and reachable for `state.list_guilds` to answer the shared-guild check; a bot-loop failure denies the login with `?auth=unavailable` rather than admitting anyone.
- `POST /api/session` is gone; `GET /api/auth/discord`, `GET /api/auth/discord/callback`, and `POST /api/logout` are public, and everything else stays behind the session guard.
