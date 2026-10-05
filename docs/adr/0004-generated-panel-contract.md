# A generated panel contract from Pydantic models

The panel's two halves can describe the same wire payload differently without anything failing, because the Quart API built dicts and the Svelte client carried JSDoc that nothing checked. Pydantic v2 models now describe every request body, response body, and SSE payload in `src/panel/schemas.py`, and those models are the single source of truth. `quart-schema` serves the OpenAPI 3.1.0 document, `typed-openapi` generates the TypeScript types and zod validators from it, and the generated artifacts are committed under `web/src/lib/contract/`. `make check` regenerates them and fails on any diff, so a model edit that was not regenerated cannot merge. The client parses every response and SSE frame through the generated zod schemas at runtime, so a server that drifts fails where it is called instead of surfacing as `undefined` in a component. This is hard to reverse: routes, the client, the tests, and the gate all depend on the generator, and the served API is now documented and validated from one object.

## Considered options

- **Hand-maintained types on each side, kept honest by tests**: rejected. Tests catch drift after the fact, and nothing names the wire shape as one object.
- **Generate the Python from the TypeScript or a neutral IDL**: rejected. Pydantic already models the API, and inverting the direction adds a second source for no gain.
- **Generate at build time instead of committing artifacts**: rejected. A production build would then depend on the codegen toolchain, editors would lose types until the first generate, and a stale artifact would not be visible as a diff.
- **`openapi-zod-client`**: rejected as deprecated. `typed-openapi` is the maintained successor and the generator the effort pinned (`--runtime zod --schemas-only --no-runtime-types --no-tree-shake-schemas`).
- **A blanket `@validate_request`**: rejected. It answers a generic `400`, which changes the pinned `404 not_found` and `401 unauthorized` codes that `tests/test_api.py` locks. Request models are documented with `@document_request`, and the handler validates through the same model to keep the wire bytes.
- **Put the SSE event name in the document**: rejected. OpenAPI cannot carry it, the name travels out of band on the `event:` line, and a discriminator property would change the pinned frame bytes. A short hand-written map from event name to schema stays in the client, backed by a parity test.

## Consequences

- `src/panel/schemas.py` is the single source of truth. `serialization`, `state`, and `actions` construct the models, so the runtime shape and the contract shape are one object.
- The server contract is `quart-schema` 0.23.0 emitting OpenAPI 3.1.0. `pages/contract.py::ContractOpenAPIProvider` hoists request and response models into `components.schemas` and documents `/api/events` as `text/event-stream`.
- The client half is one generated module, `web/src/lib/contract/panel.gen.ts`, carrying the TypeScript types and the zod schemas. No panel type is hand-maintained.
- The committed artifacts are `web/src/lib/contract/openapi.json`, `panel.gen.ts`, and `fixtures/fixtures.json`. `make contract` regenerates them, and `make check` runs that target then `git diff --exit-code` over the directory. The export is deterministic (`sort_keys`, a byte-identical test across two `PYTHONHASHSEED` values), so a stale artifact is always distinguishable from noise.
- Runtime validation is generated from the same document. A response that fails its schema becomes `ApiError{contract_violation}` through `onError` into the persistent error region, then throws. An SSE frame that fails its schema is reported the same way and dropped so the stream survives.
- The SSE event name cannot be generated. `SSE_EVENTS` in `schemas.py` maps name to payload model and `SSE_SCHEMAS` in `web/src/lib/sse.ts` maps name to schema. A pytest asserts the emitted names equal the client map, so the map cannot go stale silently.
- The generated directory is excluded from ESLint, Prettier, knip, jscpd, and Vitest coverage, and stays inside the type-check include. A broken artifact fails `typecheck` and the diff gate, not the style gates.
- The cost is a generator and a committed diff gate to maintain. Changing a wire shape is a three-step edit, regenerate, commit, and generated code is not judged as hand-written code by the style gates.
