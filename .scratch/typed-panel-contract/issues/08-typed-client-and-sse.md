# 08: Type and validate the client and SSE against the contract

**Type:** task
**Status:** resolved
**Blocked by:** 04, 06, 07

## Work

Keep `createApiClient`, the store, the toast primitive, and the error region. Each method returns the generated type for its endpoint and parses the response through the endpoint's zod schema. SSE frames parse through their payload schemas through the pinned event-name map. A validation failure surfaces as an `ApiError` into the persistent error region, matching the settled fail-loud intent. Preserve `credentials: "same-origin"` and the `onError` wiring.

Done when no client or SSE code reads `any`, Vitest covers valid and invalid payloads, and the Playwright critical paths still pass.

## Comments

Landed uncommitted for review.

- `web/src/lib/types.ts` is deleted. Wire types and zod schemas come from `web/src/lib/contract/panel.gen.ts`. App-internal aliases stay local: `AppState` in `store.ts`, `SseFrame` (plus the private `StatusFrame` / `ReloadFrame` members) in `sse.ts`. Components import wire types from `$lib/contract/panel.gen`.
- `request()` is one generic with two overloads. Bodyless: `request(path, responseSchema, { method?, silent? })`. With a body: `request(path, responseSchema, { method?, silent?, requestSchema, body })`. Both return `z.infer<typeof responseSchema>`. The body parses through `requestSchema` before serialization, the response parses through `responseSchema` before returning. No endpoint-to-schema table beyond the method list.
- Fail loud: a response that fails its schema becomes `ApiError` with code `contract_violation`, the HTTP status, routed through `onError` unless `silent`, then thrown. `credentials: "same-origin"` and the existing `onError` wiring into `errorRegion` are unchanged.
- Error bodies parse with the generated `ErrorEnvelope`; if that parse fails the client falls back to `{ code: "error", message: "Request failed" }` so an unmodeled error still surfaces.
- SSE: `parseFrame` maps `status` -> `StatusSnapshot` and `reload` -> `ReloadEvent` through a module-private `SSE_SCHEMAS` map in `web/src/lib/sse.ts`, parsing only the data body. A frame that fails JSON or its schema becomes `ApiError` `contract_violation` (status 0) through a new `onError` option on `createEventStream`, wired to `errorRegion.report` in `routes/+page.svelte`; the frame is dropped and the stream survives.
- `web/knip.json` dropped the now-stale `ignoreDependencies: ["zod"]` because `zod` is resolvable through the imported generated schemas. This is a ticket 08 side effect to fold into ticket 10's exclusion set. ESLint is unchanged.
- Vitest: `api.test.ts` gained a drifted-response contract-violation case (reported), a silent session-probe violation, and an unmodeled-error fallback case; existing fakes now send full `StatusSnapshot` payloads. `sse.test.ts` gained `parseFrame` valid status/reload cases, a schema-failure drop case, an event-name routing case, and a dropped-frame violation-reporting case. 73 tests pass; coverage floor stays 70.
- Gates: `make format` then `make check` exit 0, including Playwright 8/8 and the contract regeneration diff clean.

## Answer

Resolved.

- `web/src/lib/types.ts` deleted. `api.ts` and `sse.ts` parse through the generated zod schemas from `web/src/lib/contract/panel.gen.ts`; `store.ts`, the components, and `+page.svelte` import the generated wire types. `AppState` stays in `store.ts`, the `SseFrame` union stays in `sse.ts`.
- `request()` is one generic with bodyless and body overloads, both returning `z.infer` of the response schema; the body parses through its request schema, the response through its schema. A response parse failure becomes `ApiError{contract_violation}` through `onError` unless silent, then throws; error bodies parse through `ErrorEnvelope` with a generic fallback.
- SSE routes through the private `SSE_SCHEMAS` map (`status` -> `StatusSnapshot`, `reload` -> `ReloadEvent`); a failed frame becomes `ApiError{contract_violation}` through a new `createEventStream` `onError` wired to `errorRegion`, and is dropped so the stream survives.
- `knip.json` dropped the stale `zod` `ignoreDependencies`; no threshold lowered.
- Verified: `make format` then `make check` exit 0; `svelte-check` 0/0, ESLint 0, Prettier clean, Vitest 73/73 at coverage 96.78/89.1/98.97/97.25 against the floor of 70, `knip` 0, Playwright 8/8, contract regeneration diff clean.

Known nit, not actioned: a request-body parse failure throws the raw `ZodError`. It cannot fire because every body is built from typed arguments.
