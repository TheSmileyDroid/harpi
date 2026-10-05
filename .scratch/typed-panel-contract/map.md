# Typed panel contract: map

This is the wayfinder map for the `typed-panel-contract` effort. The spec is [spec.md](spec.md). Child tickets live in `issues/`.

## Destination

The panel runs strict TypeScript at maximum strictness against a generated, runtime-validated API contract. Pydantic models are the single source of truth, `make contract` generates the OpenAPI document, the TypeScript types, the zod validators, and the test fixtures, `make check` fails on drift and on any lowered threshold, and the bot surface is untouched.

## Notes

- Domain vocabulary is in `CONTEXT.md` (Session, Transport, Layer, Toast, Snowflake, Design language). Use those terms.
- Read before touching code: `docs/agents/architecture.md`, `docs/agents/testing.md`, `docs/agents/panel.md`, `DESIGN.md`, ADR 0003 (Snowflake IDs as strings) and ADR 0002 (volume).
- Skills for sessions: `how` to walk the panel/API/SSE runtime, `implement`/`implement-spec` to execute, `commit-conventions` before any commit, `code-review` after behavior lands, `grilling` for the decision tickets.
- Verify with `make format` then `make check`; exit 0 means done. No gate is lowered. Bun is the frontend package manager.
- This effort **carries execution into the map** (override of wayfinder's plan-only default): the decision tickets settle the route, the `task` tickets land the change. The spec already fixes the direction, so these tickets sequence the work rather than reopen it.
- Existing decisions that constrain every ticket: keep `createApiClient`, the store, and the toast/error-region semantics; big-bang to strict TS; generated artifacts committed and stale-checked; runtime zod validation on responses and SSE; `typed-openapi` for generation; `quart-schema` for the server contract and OpenAPI 3.1.

## Decisions so far

<!-- one line per closed ticket, added on resolution -->
- [01 Choose and configure the OpenAPI-to-TypeScript generator](issues/01-choose-generator.md): pin `typed-openapi` with `--runtime zod --schemas-only --no-runtime-types --no-tree-shake-schemas`; one checked module with types + zod; export must hoist models into `components.schemas` and componentize the SSE union.

- [02 Quart-schema patterns](issues/02-quart-schema-patterns.md): emits OpenAPI 3.1.0; `@validate_response(models, status)` stacked per status; `error_response` returned from `before_request` bypasses validation, but a `Response` from a validated status raises `RuntimeError` so use `@document_response` for error/SSE; SSE union is a `RootModel` with a provider override for `text/event-stream`; no `format_schema`, export via `openapi_provider.schema()`.
- [03 Decide the export mechanics and gate ordering](issues/03-export-and-gate-mechanics.md): export imports the real app and dumps `openapi_provider.schema()` with `sort_keys`; `make contract` regenerates in tree and `make check` diffs the contract directory before the frontend gates; determinism and validity are ordinary pytest; the production build consumes committed artifacts.
- [04 Shape the generated module and the typed client](issues/04-generated-module-and-client.md): committed `web/src/lib/contract/{openapi.json,panel.gen.ts,fixtures/}`; one generic `request()` takes each method's schemas; a failed parse becomes `ApiError{contract_violation}` into the error region then throws; error bodies use the envelope schema; zod 4; SSE maps the out-of-band event name to its payload schema.

- [05 Rewrite the panel models and convert the API routes](issues/05-panel-models-and-routes.md): models are the single source of truth for every request and response; `serialization`/`state`/`actions` return the models; requests validate in-handler through the same model to keep the pinned `404`/`401`/`200 []` wire; success responses use `@validate_response`, error statuses use `@document_response`; wire bytes proven unchanged.

## Not yet specified

- Whether the contract and generation approach deserves an ADR. It is hard to reverse and a real trade-off, so it likely qualifies. Decide after the route is walked.
- The exact shape of the `Snowflake` annotated type and its before-validator, and whether the int-or-digit-string acceptance needs a dedicated test beyond the existing ADR 0003 test.
- Whether Vitest coverage exclusion of the contract directory needs any config beyond an exclude glob, and how generated files interact with the coverage floor.
- Whether the strictness flags force a scoped change to SvelteKit's generated tsconfig, and how that is recorded.

## Out of scope

- A real RPC protocol (tRPC has no Python server).
- A caching or data-fetching library (`@tanstack/svelte-query` or equivalent).
- New panel features, visual redesign, or any change to endpoint behavior, business logic, or auth.
- Any change to the bot surface or its tests.
- The editor and language-server setup (a parallel session, no repo change).
