# 10: Retire the old panel

**What to build:** The old panel and its transport are gone and the repo carries one interface. This is the contract step of the cutover, and it is the only ticket where main would notice a regression, so it merges last with every gate green.

**Blocked by:** 05, 09

**Status:** ready-for-agent

- [x] htmx, the Jinja panel templates, the fragments dependency, and all HX plumbing are removed
- [x] Template-oriented tests are removed or rewritten at the API seam; no test asserts a deleted surface
- [x] The template-oriented gates go with the template tree, and no other gate is lowered to compensate
- [x] Frontend and API gates stay green, and the bot-surface tests are unedited and green
- [x] The repo is clean of stale references to the removed transport

## Comments

Removed with the old surface: `pages/index.py`, `pages/music.py`, `templates/`,
`static/` (assets, fonts, the htmx bundle, the Tailwind CSS), the root
`package.json`/`bun.lock`/`.prettierrc`/`.prettierignore` (prettier-for-Jinja
only), the `htmx-panel` skill, and the `djlint`, `jinja2-fragments`, and
`pytailwindcss` dependencies. `app.py` keeps the API/SSE blueprints, drops the
`format_duration` template filter, and serves the built Svelte SPA: `GET /`
returns `web/build/index.html`, `GET /<path:filename>` returns the built
assets. Unknown paths 404 through the existing HTML default; unknown `/api/`
paths still answer the JSON envelope because the error handler keys off the
path prefix, not the view.

Serving and gates:

- `make build` runs `bun run build` into `web/build`; `make start` builds then
  runs. `make dev` now runs Vite and Quart only (the Tailwind watch is gone).
- Playwright runs against the production build served by Quart, not the Vite
  dev server: the e2e script builds first and the only `webServer` is the
  backend. The 8 critical-path specs pass against the real static host.
- `make check` retires djlint and the template prettier check, and drops
  `templates/` from the jscpd scan. No surviving gate is lowered.
- Docker gains a `bun` frontend stage that builds `web/build`, copied into the
  runtime image; compose adds an anonymous volume at `/app/web/build` so the
  bind-mounted source tree cannot shadow the build.

Tests:

- `tests/fakes.py` is the shared home for `FakeBot`, `FakeGuild`, `FakeSession`,
  `FakeSessionManager`, `FakeReadyBot`, `playing_status`, `found_track`, and
  `patch_search`; `tests/test_api.py`, `tests/test_panel_domain.py`, and
  `web/e2e/backend.py` import from there.
- Deleted `tests/test_music_page.py`, `tests/test_index_page.py`, and
  `tests/test_panel_time_dependent_ui.py` (all assert the htmx surface, swap
  structure, or poll configuration).
- `tests/test_panel_session_integration.py` keeps its real-`PlaybackSession`
  coverage, rewritten to drive `/api/*` and assert JSON snapshots.
- `tests/test_panel_domain.py` keeps its `src/panel/` coverage; the tests for
  the deleted `search`, `require_session`, `clear_layers`, `stop`, and
  `toggle_pause` wrappers go with them.
- New `tests/test_spa.py` covers the SPA index, an asset, the HTML 404, and the
  JSON envelope on `/api/`.
- `tests/test_design_language.py` scans `web/src/app.css` and
  `web/src/**/*.svelte`; the three rules are unchanged and no green or stray red
  exists in the Svelte sources.

Deliberate cuts recorded here:

- The old panel-only behaviors with no JSON equivalent are dropped: the
  all-tracks-skipped warning `add_track` returned, `actions.search` raising on
  no results, bulk `clear_layers`, `stop`, and `toggle_pause` (play/pause are
  separate endpoints). The Svelte client and the API are the one surface.
- The htmx global indicator bar and the `htmx-request` button blink were
  htmx-only chrome; per-action feedback now reads through the disabled button.
  DESIGN.md lost both.
- `SHELL_ASSETS` (the SSE reload channel) now watches `web/src/app.html` and
  `web/src/app.css`, the surviving shell-level assets.
- Docs updated in the same cut: `AGENTS.md`, `CONTEXT.md`, `PRODUCT.md`,
  `README.md`, `DESIGN.md`, `docs/agents/architecture.md`,
  `docs/agents/panel.md`, `docs/agents/testing.md`, `docs/agents/taste.md`, and
  ADR 0002.
