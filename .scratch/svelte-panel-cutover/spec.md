# Svelte panel cutover

Status: done

## Problem Statement

The web panel is built on htmx, and its owner finds it hard to test, style, and change. Four concrete pains came out of the review: fragment logic scattered between `hx-*` attributes and the Python handlers that feed them, styling tied to swap boundaries rather than to the page, tests that assert transport headers instead of user-visible behavior, and poll configuration littering every template. Alongside that, the live-editing loop that was supposed to make visual iteration pleasant was brittle: no browser reload on edits, a polling helper that died silently mid-session, and a variant session that stranded markup in the source tree.

The owner rejects React-style stacks on runtime and quality grounds, does not care about keeping Jinja, and wants beauty of result treated as a first-class outcome. Two research rounds were run to settle the direction instead of guessing, and the results are linked under Further Notes.

## Solution

The panel becomes a SvelteKit app in single-page-app mode, built by Vite and served as static assets by Quart, which shrinks to a JSON API with session auth. Live state arrives over Server-Sent Events from Quart instead of markup-declared polling. htmx, the Jinja panel templates, and their attributes leave the repo.

The work lands as a single cutover on a branch, with a Vite-shaped dev loop landing first on main as its own small green commit. The bot surface does not change, and its tests stay unedited and green. JavaScript quality gates arrive at the same strength as the Python ones, and the Playwright suite lives inside `make check` so a red browser test blocks like a red lint.

## User Stories

1. As the bot owner, I want the panel's interactive surfaces rebuilt as Svelte components, so that styling lives with the component that owns it instead of at swap boundaries.
2. As the bot owner, I want every panel behavior I have today either kept or explicitly dropped during the cutover, so that nothing disappears by accident.
3. As the bot owner, I want to connect the bot to a voice channel from the panel, so that a listening session starts without touching Discord.
4. As the bot owner, I want a guild selector backed by the guild list I actually share with the bot, so that multi-guild state stays unambiguous.
5. As the bot owner, I want to search YouTube from the panel and queue a result, so that adding music is one interaction.
6. As the bot owner, I want queue management (select, remove, clear, reorder where it exists today), so playback is controllable from the panel alone.
7. As the bot owner, I want layer management (add a layer, remove one, set its volume), so mixing control stays in one place.
8. As the bot owner, I want transport controls (play, pause, skip, previous, loop), so playback reacts immediately.
9. As the bot owner, I want seek and volume to feel live while I drag, so the panel behaves like a player and not a form.
10. As the bot owner, I want playback position and bot status to update without a reload, so the panel reflects reality and bot state explains itself.
11. As the bot owner, I want those updates over SSE, so no template carries poll configuration and no background refresh shows a loading state.
12. As the bot owner, I want toasts for confirmations and a persistent inline error region for failures, so the panel never fails silently.
13. As the bot owner, I want the client to recover from a dropped SSE stream, so live state returns without a manual reload.
14. As the bot owner, I want session auth on the API, so the new JSON surface is not open by accident.
15. As the bot owner, I want my session to persist across server restarts, so signing in is not a per-visit chore.
16. As the bot owner, I want the auth boundary enforced server-side on every endpoint, so trust does not depend on the UI hiding things.
17. As the bot owner, I want the API bound to localhost by default, so the new surface does not widen exposure.
18. As the bot owner, I want the current visual design preserved through the cutover, so an architecture change does not regress beauty.
19. As the bot owner, I want a polish pass after the cutover, so beauty improves once the architecture is stable.
20. As the bot owner, I want the panel to keep its responsive behavior, so the fixed chrome rules for the status strip, transport bar, and toasts still hold on mobile.
21. As the bot owner, I want hot module reload for the frontend and a reload signal for server-rendered shell changes, so edits appear without a manual refresh.
22. As the bot owner, I want one command to boot the whole dev loop, so starting work is trivial.
23. As the bot owner, I want the cutover on a branch with gates green at merge, so main never goes red.
24. As the bot owner, I want `make check` to include the JavaScript gates, so interface work cannot merge with a red lint, type, coverage, or duplication state.
25. As the bot owner, I want JavaScript gates at least as strict as the Python ones, so quality is not bimodal across the repo.
26. As the bot owner, I want Playwright to cover the critical paths in a real browser, so the assembled app is proven end to end.
27. As the bot owner, I want Vitest to cover pure frontend logic, so a failure points at a unit instead of at a click.
28. As the bot owner, I want pytest to keep driving the API through the app's own HTTP seam, so the API contract gets the same class of tests the panel has today.
29. As the bot owner, I want the Discord bot's code and tests untouched, so music does not die during a UI rewrite.
30. As the bot owner, I want bot failures to keep surfacing as they do now, so a UI rewrite never mutes an alert.
31. As the bot owner, I want no error to require a bot restart, so the API layer inherits the same rule as the bot.
32. As the bot owner, I want htmx, the Jinja panel fragments, and their attributes gone from the repo, so no dead transport lingers.
33. As the bot owner, I want the API contract written down in the spec, so frontend and backend cannot drift silently.
34. As a future agent, I want the settled decisions linked to the research that justified them, so rationale is recoverable without replaying a conversation.
35. As the bot owner, I want process orchestration deferred to its own piece of work, so this cutover stays focused.

## Implementation Decisions

Direction. SvelteKit in SPA mode is the frontend. Quart serves the built assets and a JSON API. No SSR and no Node process in production. The single-process constraint is explicitly dropped for this work, but this spec does not introduce a second production process: the API and static hosting stay in the Quart process, and the bot keeps running inside it as today.

Transport. Live state (bot status, guild state, playback position and mode) is pushed over SSE from Quart. Every user action is a JSON request and response. htmx is removed, along with the Jinja panel templates, the fragments dependency, the `HX-*` header handling, the out-of-band error markup, and the trigger-header toast mechanism. The current toast and global-indicator behaviors are reimplemented client-side, preserving their intent: confirmations are transient, failures are persistent, background updates are visually silent.

Auth. Quart issues a session cookie after a token exchange. The token comes from the environment, the same secret-handling path the bot already uses. Every endpoint except the token exchange and static assets requires a valid session. Cookies are HttpOnly and SameSite, and the API is bound to localhost by default. No OAuth provider is introduced.

Frontend modules. A SvelteKit app with two routes matching today's surfaces (status, music). A client state store owns guild selection, bot status, playback state, and the search box state. An SSE client module owns connection, reconnect, and event dispatch into the store. An API client module wraps fetch with the session and normalizes error payloads into the persistent error region. Components own their own styles.

Backend modules. The existing page blueprint becomes an API blueprint; the render helpers, block whitelist, fragment routing, and template context builders are deleted with their tests. Domain access keeps going through the bot state layer, unchanged. The status endpoint returns JSON instead of a rendered fragment.

API contract. Endpoints cover: token exchange and session check; bot status; guild list and guild selection; connect and disconnect; search; queue, queue actions, and layer actions; transport actions (play, pause, skip, previous, loop); seek; volume. Each returns a stable JSON shape and a machine-readable error object. The exact schema is fixed at implementation time and frozen in the spec's issue tickets.

Dev loop. Vite serves the frontend with HMR at `:5173` and proxies `/api` to Quart at `:8000`. Quart exposes `GET /api/events` as an event stream: it opens with the comment frame `: connected`, and when a shell-level asset changes it sends `event: reload` with JSON data `{"scope": "shell"}`. Shell-level assets are `templates/`, `static/css/app.css`, and `web/src/app.html`. Status events extend this same stream in a later ticket. `make dev` boots the Tailwind watch, the Vite dev server, and Quart together. The loop work item lands on main first, with `make check` green, before the cutover branch opens.

Cutover shape. One branch. Old and new do not coexist beyond the loop commit. Panel parity is not sacred: any behavior that fights the new architecture may be cut or simplified during the cutover, recorded in the cutover ticket. The existing visual design is preserved through the cutover; design improvement is a separate follow-up pass.

Gates. djlint, the Jinja prettier plugin, and the template-oriented duplication checks retire with the template tree. Their replacements match the Python set: linting, formatting, type checking for the frontend, a coverage floor for the frontend suite, dead-code detection, and duplication checking across the JavaScript sources. Playwright runs inside `make check`. No gate is lowered or disabled to make the cutover pass; if a gate cannot be satisfied, the cause gets fixed or the dead gate is deleted with justification.

Bot surface. Bot code and its tests stay as they are. `src/` changes are permitted only where the API genuinely needs a different domain shape, and every existing bot-side test stays green without edits.

## Testing Decisions

A good test asserts external behavior: a request and its response, a rendered outcome, a state transition a user could describe. No test asserts internal wiring, header plumbing, or implementation names.

Three seams, each at its highest useful point. Pytest drives the Quart ASGI app over HTTP and asserts the API contract, which is the same seam today's panel tests use, so their intent carries over while their transport assertions go away. Vitest covers pure frontend logic with no browser: the client state store's reducers and transitions, the SSE event handling, and formatting helpers. Playwright drives the assembled app for a critical-path set: connect, search and queue, transport actions with live position updates, layer and volume actions, error surfacing, and SSE reconnect. Critical paths are chosen once, at implementation time, and kept small enough that the suite stays fast inside `make check`.

Prior art: the current pytest-over-ASGI panel tests and the session integration tests define the API seam's style; Playwright is already a pinned dependency; the repo already believes in coverage floors, dead-code detection, and duplication limits, so the frontend inherits those standards rather than inventing new ones.

## Out of Scope

Process orchestration and supervision (explicitly deferred, its own future piece). Visual redesign beyond preserving the current design. Re-introducing or re-evaluating the outside live-editing tool, which is decided after the loop exists. Discord command surface changes. OAuth or any external identity provider. SSR of panel pages. New panel features that parity does not require.

## Further Notes

Two research rounds back the direction. The first covers frontend architectures against htmx and lives at `~/.config/opencode/research/2026-09-24-what-frontend-architecture-should-harpi-s-quart-ji/report.md`; the second covers Svelte and the compiled alternatives at `~/.config/opencode/research/2026-09-24-which-frontend-architecture-should-harpi-s-quart-p/report.md`. Each folder carries its source scorecard, computed confidence tiers, and judge audit.

The auth mechanism is the one implementation decision made at spec time rather than in review: session cookie exchanged from an environment token. It was chosen because the owner asked for session or token auth and because it adds no external dependency; Discord OAuth stays out of scope unless requested.

AGENTS.md's "we never compromise" rules still bind: music does not die while playing, bot state explains itself, and nothing fails in silence. The panel rewrite inherits all three, and the preserved bot tests are how the first one is enforced mechanically.

## API contract

Ticket 03 freezes the wire contract below. Tickets 04 to 09 consume it; any change is a spec edit, not a handler edit.

### Auth

`PANEL_TOKEN` (`src/config.py`, `.env.example`) is the only credential. `POST /api/session` compares it in constant time and, on match, writes a signed session cookie holding `authenticated: true` (Quart session, `HttpOnly`, `SameSite=Lax`, 30-day lifetime). The cookie is stateless, so the session survives a backend restart as long as `SECRET_KEY` is stable.

The whole `/api/` surface sits behind the session guard in `app.py`. Public: `POST /api/session` and static assets only. Every other `/api/` path, defined or not (the bare `/api` included), returns `401` without a valid session. `GET /api/session` is guarded and answers `200 {"authenticated": true}` when the cookie is valid.

### Error envelope

Every API error uses one shape:

```json
{"error": {"code": "unauthorized", "message": "Authentication required"}}
```

Codes: `unauthorized` (401), `not_found` (404), `method_not_allowed` (405), `internal_error` (500). The `/api/` 404, 405, and 500 handlers return this envelope; non-API routes keep Quart's HTML defaults. URL slashes are not merged, so a doubled slash under `/api/` 404s through the envelope rather than redirecting to HTML.

### Endpoints

`POST /api/session`
- Request: `{"token": string}`
- `200`: `{"authenticated": true}` plus the session cookie.
- `401`: envelope, `unauthorized`. Wrong, missing, or unconfigured token.

`GET /api/session`
- `200`: `{"authenticated": true}`.
- `401`: envelope, `unauthorized`.

`GET /api/status`
- `200`: the status snapshot below.
- `401`: envelope, `unauthorized`.

```json
{
  "bot": {"online": true},
  "guild_id": 123,
  "connection": {"connected": true, "channel_id": 42},
  "playback": {
    "guild_id": 123,
    "connected": true,
    "is_playing": true,
    "is_paused": false,
    "current_music": {"title": "t", "url": "u", "uploader": "a", "duration": 120, "thumbnail": "x"},
    "queue": [],
    "layers": [{"id": "l1", "title": "t", "url": "u", "volume": 0.7, "thumbnail": "x"}],
    "loop_mode": "OFF",
    "volume": 0.7,
    "progress": 0.0,
    "channel_id": 42
  }
}
```

`bot.online` is server truth. `guild_id` is the session's selection (ticket 06 owns selection; until then it rides the existing session cookie). `connection` mirrors the session's voice state. `playback` is null when no session exists for the selection. `loop_mode` is `OFF`, `TRACK`, or `QUEUE`.

`GET /api/events`
- `200`: `text/event-stream`, guarded by the session cookie (browsers send it automatically).
- `401`: envelope, `unauthorized`.

SSE frames:

| Frame | Data | When |
| --- | --- | --- |
| `: connected` | none | First frame of every connection. |
| `event: status` | Full status snapshot, same shape as `GET /api/status`. | Immediately on connect, then on every change. Full snapshot each time, so a reconnect resyncs without duplicated state. |
| `event: reload` | `{"scope": "shell"}` | A shell-level asset changed (`templates/`, `static/css/app.css`, `web/src/app.html`). |

### Reserved for tickets 06 to 09

These paths are part of the contract but their request and response schemas are fixed in their own ticket. All are guarded, all errors use the envelope, and each mutation answers with the fresh status snapshot so the client never guesses.

- Ticket 06, connect and guild selection: `GET /api/guilds`, `GET /api/guilds/{guild_id}/channels`, `POST /api/connect`, `POST /api/disconnect`.
- Ticket 07, search and queue: `POST /api/search`, `POST /api/queue`, `POST /api/queue/remove`, `POST /api/queue/clear`.
- Ticket 08, transport, seek, and volume: `POST /api/playback/pause`, `POST /api/playback/resume`, `POST /api/playback/skip`, `POST /api/playback/previous`, `POST /api/playback/loop`, `POST /api/playback/seek`, `POST /api/playback/volume`.
- Ticket 09, layers: `POST /api/layers`, `POST /api/layers/remove`, `POST /api/layers/volume`.

### Coexistence on this branch

The old htmx routes (`/`, `/status`, `/music`) stay open until ticket 10 deletes them, so the branch stays green at every commit. This overrides the "old and new do not coexist beyond the loop commit" line under Cutover shape. The gap is bounded: only the new `/api/` surface is a contract, and ticket 10 is the only place main would notice the old panel leave.

### Binding

`HOST` defaults to `127.0.0.1` and stays overridable through `HOST` or `--host`; production Docker passes `--host 0.0.0.0` explicitly.
