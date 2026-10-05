# 05: Rewrite the panel models and convert the API routes

**Type:** task
**Status:** resolved
**Blocked by:** 02

## Work

Pydantic models become the single source of truth for every request body, response body, and SSE event payload. The dict builders in `src/panel/serialization.py` become model constructors. A `Snowflake` annotated type carries ADR 0003: a string on the wire, accepting an int or an ASCII-digit string on input. The hand parsers in `pages/api.py` retire in favor of typed fields.

Request handling preserves the pinned wire behavior (decision recorded in a comment below): request bodies are modeled and documented with `@document_request`, validated in the handler through the Pydantic model, and a validation failure maps to the exact `error_response` code and message the route returns today. Success responses use `@validate_response` with the response model, the error envelope becomes a modeled response, the status snapshot is the shared response type for `GET /api/status` and every mutation, and `/api/events` is documented as `text/event-stream`.

Done when pytest over the ASGI app is green, Snowflake exactness and snapshot parity still pass, and `make check` is green for the Python side.

## Comments

A blanket `@validate_request` conversion was rejected during implementation. It answers a generic `400`, and `tests/test_api.py` pins `404 not_found` (queue, transport, layers), `401` (session exchange), and `200 {"results": []}` (search without a term), so the conversion would change endpoint behavior that the spec puts out of scope. Request validation therefore runs in the handler with the same Pydantic model, mapped to the existing envelope. Chosen 2026-10-04.

Progress 2026-10-04: models (`src/panel/schemas.py`) and the route conversion landed; `pages/api.py` now uses `@validate_response`/`@document_request`/`@document_response` and parses requests through the models; `QuartSchema(app)` is wired. All pytest (560), ruff, ty, vulture, CRAP, jscpd, and the frontend gates pass. `make check` fails only at Playwright because no browser binary is installed (`cd web && bunx playwright install chromium`). The `serialization.py` to model-constructors line is not done; serialization still returns dicts validated at the route boundary, so `tests/test_panel_domain.py` stayed green. Decide whether to convert it or amend the spec sentence. Work is uncommitted; see `/tmp/opencode/handoff-typed-panel-contract.md`.

## Answer

Resolved 2026-10-04. The `serialization.py` line was done, not amended.

`serialization.py` now returns `Track`, `Layer`, `PlaybackStatus`, `Guild`, and `Channel` models; `state.list_guilds`, `state.list_voice_channels`, `state.guild_status`, and `state.status_snapshot` return the models; `actions.search_tracks` returns `list[Track]`. `guild_status` reads `playback.connected`/`playback.channel_id` by attribute, `pages/api.py` reads `channel.id`, and `pages/events.py` dumps `StatusSnapshot` through `_frame`.

Reason the conversion is the right call: the wire path was already `model_dump()`. `@validate_response` converts the handler's dict to the model and returns the model, and `quart_schema.extension.wrap_make_response` dumps that model before Quart serializes it. Returning the model from the domain seam therefore cannot change the wire. Proven with a raw-bytes capture of `/api/session`, `/api/status`, `/api/guilds`, and `/api/guilds/{id}/channels` before and after: byte-identical. `tests/test_events.py` pins the SSE frames and stayed green, so the SSE bytes are identical too. The conversion cost six expectations in `tests/test_panel_domain.py` (`model_dump()` or attribute access) plus the `state`/`actions` return annotations; the tests now assert the contract shape directly.

Two mechanics fell out of the conversion: `Snowflake` is a string at the static type level (the `BeforeValidator` coerces ints at runtime), so `serialization.snowflake`/`optional_snowflake` pass a `str` into the constructors; and `_frame` in `pages/events.py` accepts `dict | StatusSnapshot` so the pinned SSE tests keep passing dicts.

Verified: `make check` exit 0 (560 pytest, ruff, ty, vulture, CRAP, jscpd, all frontend gates, 8 e2e).
