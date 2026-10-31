# Panel and API work

Commands and panel are one feature on two surfaces. Fixing one is not fixing the feature. Before calling music work done, walk this list:

- **Surfaces.** play, pause, skip, seek, queue and layers are reachable from both a `MusicCog` command and a `pages/api.py` endpoint. If you added one, check the other.
- **Reverse states.** If you added a way in, add the way out. Connect needs disconnect. Loop on needs loop off. A one-way door is a bug.
- **Both loops.** API code that touches discord.py internals goes through `run_on_bot_loop`, never calls the coroutine directly. See [architecture.md](architecture.md).
- **One contract.** Pydantic models in `src/panel/schemas.py` are the single source of truth. `make contract` exports the OpenAPI document, generates the TypeScript types and the zod validators into `web/src/lib/contract/`, and emits the test fixtures. The committed artifacts are regenerated and diffed in `make check`, so the Svelte client and the API cannot drift. Every music mutation answers the fresh `state.status_snapshot`, and the client applies it instead of guessing; campaign mutations answer the accepted resource (a sheet write answers its `SheetDetail`, ADR 0012). pytest pins that parity.

## The Svelte panel

`web/` is a SvelteKit single-page app (SSR off, adapter-static) built by Vite. In development `make dev` runs Vite at `:5173` with hot module reload, proxying `/api` to Quart at `:8000`. In production `make build` emits `web/build` and Quart serves it at `/`; the Docker image builds it in a frontend stage.

The client owns state in a store (`web/src/lib/store.ts`), opens the SSE stream (`web/src/lib/sse.ts`), and wraps fetch with the session and the error region (`web/src/lib/api.ts`). Components own their own styles. Before styling a surface, read [DESIGN.md](../../DESIGN.md); the rules a test can judge live in `tests/test_design_language.py`.

The contract is committed under `web/src/lib/contract/`: the exported `openapi.json`, the generated `panel.gen.ts` (types plus zod schemas), and `fixtures/fixtures.json`. Run `make contract` after any model change. `make check` runs that target and fails on a diff, so a model edit that was not regenerated cannot merge. Responses and SSE frames parse through the generated schemas at runtime, and a payload that fails its schema is reported as a `contract_violation` in the persistent error region instead of reaching a component.

Mutations are JSON requests and every one answers `200` with the fresh status snapshot. Live state arrives over SSE from `GET /api/events`. One sampler per guild polls once and every open stream subscribes to it (ADR 0009): the full `status` frame goes out only when something other than the position changes, a small `position` frame every 5s and on any jump, `presence` and `directory` when they change, and a `heartbeat` every 5s that carries no state. Every `POST` pokes the sampler, so a panel mutation lands immediately for every viewer instead of on the next poll. A selection change restarts the stream; queue, transport and layer changes do not.

The panel treats 15s without a `status`, `position`, or `directory` frame as stale: it shows the hazard-red STALE tag and dims the readouts while keeping every control live. Missing heartbeats, not missing values, mean the link is gone; the stream client reconnects with backoff and the page refetches `/api/status` on reconnect and on `visibilitychange`.
