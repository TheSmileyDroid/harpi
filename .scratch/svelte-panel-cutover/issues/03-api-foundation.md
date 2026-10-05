# 03: API foundation

**What to build:** The app answers a JSON API behind a session boundary and exposes a live event stream. Signing in exchanges a token from the environment for a session cookie, unauthenticated calls are rejected server-side, and bot status arrives as SSE events that reconnect after a drop. Everything here is verifiable without a browser.

**Blocked by:** 02

**Status:** done

- [x] Token exchange issues an HttpOnly session cookie; missing or bad tokens are rejected
- [x] Every non-public endpoint returns 401 without a valid session
- [x] The status endpoint returns a documented JSON shape
- [x] The SSE stream emits status events and recovers from a dropped connection without duplicating state
- [x] pytest covers the contract, auth rejection, and the event shape at the app's HTTP seam
- [x] The API binds to localhost by default

## Comments

Contract frozen in `spec.md` under "API contract". Auth reads `PANEL_TOKEN` through `Settings.from_env()`; the signed cookie carries `authenticated` and the existing `guild_id` selection. The old htmx routes stay open until ticket 10, so route-level `/api/` guarding in `app.py` is the only boundary; ticket 04 signs in with `POST /api/session` and reads `GET /api/status` plus the `status` SSE event.

Ticket 06 owns guild selection. Until then `GET /api/status` and the SSE snapshot read `guild_id` from the existing session cookie, so ticket 04 can render a selected guild only after ticket 06 writes one.
