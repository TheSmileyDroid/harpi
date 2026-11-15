# Panel and API work

Commands and panel are one feature on two surfaces. Fixing one is not fixing the feature. Before calling music work done, walk this list:

- **Surfaces.** play, pause, skip, seek, queue and layers are reachable from both a `MusicCog` command and a `pages/api.py` endpoint. If you added one, check the other.
- **Reverse states.** If you added a way in, add the way out. Connect needs disconnect. Loop on needs loop off. A one-way door is a bug.
- **Both loops.** API code that touches discord.py internals goes through `run_on_bot_loop`, never calls the coroutine directly. See [architecture.md](architecture.md).
- **One contract.** `src/panel/schemas.py` is the single source of truth; the client types, zod schemas and fixtures are generated from it and diffed in `make check`. Every music mutation answers the fresh `state.status_snapshot`, and the client applies it instead of guessing. See [ADR 0004](../adr/README.md#adr-0004--the-panel-contract-is-generated-from-pydantic).

## The Svelte panel

`web/` is a SvelteKit single-page app (SSR off, adapter-static) built by Vite. In development `make dev` runs Vite at `:5173` with hot module reload, proxying `/api` to Quart at `:8000`. In production `make build` emits `web/build` and Quart serves it at `/`; the Docker image builds it in a frontend stage.

The client keeps state in `web/src/lib/store.ts`, opens the stream in `sse.ts` and wraps fetch in `api.ts`. Components own their own styles. Before styling a surface, read [DESIGN.md](../../DESIGN.md); the rules a test can judge live in `tests/test_design_language.py`.

Live state arrives over SSE from `GET /api/events`; the frame policy is [ADR 0009](../adr/README.md#adr-0009--one-sampler-per-guild-feeds-every-stream). The panel treats 15s without a `status`, `position`, or `directory` frame as stale: it shows the hazard-red STALE tag and dims the readouts while keeping every control live. Missing heartbeats, not missing values, mean the link is gone; the stream client reconnects with backoff and the page refetches `/api/status` on reconnect and on `visibilitychange`.
