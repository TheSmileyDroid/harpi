# Strict TypeScript and a typed panel contract

Status: ready-for-agent

## Problem Statement

The panel's two halves can drift apart without anything failing. The Quart API in `pages/api.py` builds plain dicts and parses request fields by hand, and the Svelte client in `web/` is plain JavaScript with JSDoc annotations that describe payloads but do not check them. A field renamed on the server, a status code that stops matching, or an SSE frame whose shape changes all reach the browser as `undefined` somewhere deep in a component. Nothing in the type system or in `make check` names the wire shape as a contract.

Two concrete rules already live only in prose and tests: Snowflake identifiers cross the wire as strings (ADR 0003), and every mutation answers the fresh status snapshot so the client never guesses. Both are easy to break by accident because no single source of truth produces both the server type and the browser type.

## Solution

The panel becomes strict TypeScript at maximum strictness, and the API gains one generated contract that neither side can drift from. Pydantic models in Python become the single source of truth for every request body, response body, and SSE event payload. `quart-schema` validates those models on the Quart routes and serves an OpenAPI 3.1 document. A `make contract` step exports the document and generates the TypeScript types plus zod schemas that the panel consumes, alongside fixtures emitted from the same models. The generated artifacts are committed, so production builds stay hermetic and editors resolve types immediately, and `make check` regenerates them and fails on any diff.

The client keeps its current shape. `createApiClient`, the store, the persistent error region, and the toasts stay. What changes is that responses and SSE frames are parsed through the generated zod schemas, and every method carries the generated types instead of `any`. The bot surface does not change.

## User Stories

1. As the bot owner, I want the panel in strict TypeScript, so a type error fails the gate instead of reaching the browser.
2. As the bot owner, I want every strictness flag on, so the panel is checked as hard as it can be.
3. As the bot owner, I want one source of truth for the wire shape, so the API and the client cannot describe the same payload differently.
4. As the bot owner, I want the server to validate every request body against that source of truth, so malformed input is rejected at the boundary.
5. As the bot owner, I want the server to validate every response body against that source of truth, so a serialization slip fails on the server, not in the panel.
6. As the bot owner, I want the client to validate every response at runtime, so a server that drifts is caught where it is called.
7. As the bot owner, I want the client to validate every SSE frame at runtime, so a changed live payload surfaces immediately.
8. As the bot owner, I want an OpenAPI 3.1 document for the panel API, so the contract is inspectable without reading handlers.
9. As the bot owner, I want the TypeScript types generated from that document, so no panel type is hand-maintained.
10. As the bot owner, I want the runtime validators generated from the same document, so types and checks cannot disagree.
11. As the bot owner, I want Snowflake identifiers typed as strings end to end, so ADR 0003 is enforced by the type system and not only by tests.
12. As the bot owner, I want a Snowflake request field to accept an int or an ASCII-digit string, so `POST /api/connect` keeps tolerating both.
13. As the bot owner, I want every mutation's response typed as the status snapshot, so the client applies server truth and never guesses.
14. As the bot owner, I want the error envelope modeled, so error handling is typed on both sides.
15. As the bot owner, I want SSE events typed, so `status` and `reload` payloads are validated rather than parsed as `any`.
16. As the bot owner, I want a test that the emitted SSE event names match the registered event schemas, so the out-of-band event name cannot drift.
17. As the bot owner, I want the generated contract committed, so a production build does not depend on the codegen toolchain.
18. As the bot owner, I want a single `make` target that regenerates the contract, so refreshing it is one command.
19. As the bot owner, I want `make check` to regenerate the contract and fail on a diff, so a model edit without regeneration cannot merge.
20. As the bot owner, I want the export to be deterministic, so a stale artifact is always distinguishable from noise.
21. As the bot owner, I want the generated files excluded from lint, format, dead-code, duplication, and coverage gates, so machinery is not judged as hand-written code.
22. As the bot owner, I want the generated files still type-checked, so a broken artifact fails the gate.
23. As the bot owner, I want test fixtures emitted from the models, so frontend fakes cannot drift from the wire shape.
24. As the bot owner, I want a test that every fixture parses through its schema, so fixtures are proven valid.
25. As the bot owner, I want the existing client shape kept, so the error region and toast semantics do not regress.
26. As the bot owner, I want the session cookie and same-origin credentials preserved, so auth keeps working.
27. As the bot owner, I want `ApiError` and the error region preserved, so failures still surface persistently.
28. As the bot owner, I want toasts preserved as transient confirmations, so the toast and error split stays intact.
29. As the bot owner, I want no quality threshold lowered, so the migration cannot buy itself room by weakening a gate.
30. As the bot owner, I want the coverage floor to hold, so the migration adds its own tests instead of eroding coverage.
31. As the bot owner, I want the bot surface untouched and its tests unedited, so music does not die during a panel change.
32. As the bot owner, I want bun to remain the frontend package manager, so no competing lockfile appears.
33. As the bot owner, I want the panel to keep working during the migration, so `make check` is green at the end and the diff is reviewable by directory.
34. As a future agent, I want the contract decisions written down in this spec and the ADRs, so the rationale survives the session.
35. As a future agent, I want the strictness dial and the generator pinned in one config, so an editor and CI agree.

## Implementation Decisions

**Source of truth.** Pydantic v2 models describe every request body, response body, and SSE event payload. They live in the panel domain seam, next to the serialization the API already uses, not in the Quart layer. The existing dict builders in `src/panel/serialization.py` become model constructors, so the runtime shape and the contract shape are one object.

**Snowflakes.** A `Snowflake` annotated type carries the ADR 0003 rule: it is a string on the wire, and it accepts an int or an ASCII-digit string on input through a before-validator, preserving the behavior of the hand-written `_snowflake_field`. The three hand parsers in `pages/api.py` (`_snowflake_field`, `_string_field`, `_float_field`) retire in favor of typed fields.

**Server validation and documentation.** `quart-schema` (already a declared dependency, version 0.23.0, which emits OpenAPI 3.1.0 and serves it at `/openapi.json`) wires the models into the routes. Success responses use `@validate_response` with the response model, including the status snapshot as the single response type for `GET /api/status` and every mutation. Request bodies are modeled and documented with `@document_request`, but validation runs in the handler through the same Pydantic model, and a failure is mapped to the exact `error_response` code and message the route returns today (`404 not_found` for a missing or malformed field, `401 unauthorized` for the session exchange). This preserves the pinned wire behavior that `tests/test_api.py` locks; a blanket `@validate_request` would answer a generic `400` and change it. The error envelope becomes a modeled response documented on each route, and `/api/events` is documented as `text/event-stream` with the event payload components.

**SSE dispatch.** OpenAPI cannot express the SSE event name, which travels out of band on the `event:` line. The payload schemas are generated; a short hand-written map from event name to schema stays in the SSE client; a pytest asserts the emitted event names equal the registered schema names, so the map cannot go stale silently.

**Contract export.** A script exports the OpenAPI document from the Quart app without a running server and writes it under the panel's contract directory. `typed-openapi` (the maintained successor to the deprecated `openapi-zod-client`) reads that document and generates the TypeScript types plus zod schemas into one generated module. The same `make contract` target emits test fixtures from the models.

**Artifacts.** The OpenAPI document, the generated TypeScript module, and the fixtures are committed under a contract directory in the frontend. `make contract` regenerates them. `make check` runs `make contract` and then a `git diff --exit-code` over the contract directory, so a model edit that was not regenerated fails the gate. A pytest asserts the export is valid 3.1 and byte-identical across two runs.

**Client.** `createApiClient` and the store stay. Each method returns the generated type for its endpoint and parses the response with the endpoint's zod schema. SSE frames parse through their payload schemas. `ApiError`, the same-origin credentials, and the `onError` wiring into the persistent error region stay as they are. No caching or data-fetching library is introduced.

**Strictness.** The frontend moves to a strict `tsconfig` with `strict`, `noUncheckedIndexedAccess`, `exactOptionalPropertyTypes`, `noImplicitOverride`, `noFallthroughCasesInSwitch`, `isolatedModules`, and `verbatimModuleSyntax`. The migration is big-bang: every source file is renamed to TypeScript and every type error fixed before the gate is green again. The end state has no `allowJs`, and `svelte-check` and CI share the config. If `exactOptionalPropertyTypes` fights SvelteKit's generated config, we scope the conflict after seeing the errors rather than dropping the flag up front.

**Gates.** The contract directory is excluded from ESLint, Prettier, knip, jscpd, and Vitest coverage, and remains inside the type-check include. `knip.json` and the ESLint flat config gain the TypeScript globs the migration needs. No threshold is lowered.

## Testing Decisions

A good test asserts external behavior through a stable seam. It does not assert handler internals, generated names, or wiring. Existing seams are preferred and only one new seam is added.

- **pytest over the ASGI app** (the existing API seam) asserts the wire contract: request validation rejects malformed bodies, every mutation answers the status snapshot, Snowflake IDs stay exact strings, and the error envelope holds. The existing parity assertions carry over.
- **pytest for the contract export** is the new seam: it asserts the document is valid OpenAPI 3.1, that its SSE event names match the schema registry, and that two exports are byte-identical.
- **Vitest** keeps covering pure frontend logic: the client parses valid payloads and throws on invalid ones, the SSE dispatcher routes each event name to its schema, and every generated fixture parses through its schema.
- **Playwright** keeps the critical-path set as it is. The strict rewrite and the generated client must not change any user-visible behavior, so the existing specs are the regression net.

Prior art: the pytest-over-ASGI panel tests and the session integration tests define the API seam; the current Vitest units define the client seam; the Playwright suite already covers the assembled app.

## Out of Scope

A real RPC protocol. tRPC has no Python server, and the project already settled on REST plus a generated contract. A data-fetching or caching library such as `@tanstack/svelte-query`. Any change to endpoint behavior, business logic, or the auth mechanism. New panel features. Visual redesign. The editor and language-server setup happening in a parallel session. Any change to the bot surface or its tests.

## Further Notes

- This spec comes from the handoff at `/tmp/opencode/handoff-strict-ts-rpc.md` and the grilling that settled each open decision.
- Relevant decisions: ADR 0003 (Snowflake IDs as strings on the wire) and ADR 0002 (perceptual volume slider). The contract must preserve both. This spec extends ADR 0003 by moving its rule into the type system.
- `quart-schema` 0.23.0 emits OpenAPI 3.1.0 and ships a Pydantic bridge, so the server side needs no new dependency. `openapi-zod-client` is deprecated in favor of `typed-openapi`; the generator choice follows that.
- One risk to resolve during implementation: the export script imports the Quart app to emit the document, and `app.py` reads settings at import time. The export must run in `make check` without a live bot, so the script either builds a minimal app or the gate supplies the environment. The deterministic-export test is the check that this holds.
- The vulture `ignore_names` in `pyproject.toml` still names an `app.py` `ServerStatusModel` that no longer exists. Adding the real models is the moment to clean that list.
- Bun stays the frontend package manager. No `package-lock.json` or `pnpm-lock.yaml` is introduced.
