# 06: Author the export script and the make target

**Type:** task
**Status:** resolved
**Blocked by:** 03, 05

## Work

Add the export script that emits the OpenAPI document from the Quart app without a live bot, and the generator step that produces the TypeScript types, the zod validators, and the fixtures from it. Add the `make contract` target and wire the regenerate-then-diff step into `make check`. Commit the generated artifacts under the contract directory.

Done when `make contract` regenerates the artifacts deterministically, `make check` fails when a model edit is not regenerated, and the deterministic-export and validity tests pass.

## Comments

Decision 2026-10-04: the export is `tools/export_contract.py`, which imports the real app and writes `app.json.dumps(provider.schema(), indent=2, sort_keys=True)`. `pages/contract.py::ContractOpenAPIProvider` overrides `build_request_body` and `build_response_object` to hoist the root model into `components.schemas` and replace the inline schema with a `$ref`, so `typed-openapi --schemas-only` sees every model. `build_response_object` swaps the content key to `text/event-stream` when the model carries `__sse__`. The route documents `SseEnvelope(RootModel[StatusSnapshot | ReloadEvent])` with `@document_response`.

Decision 2026-10-04: the SSE union is a plain `anyOf` of payload models, not `oneOf` + `discriminator`. The real frames carry the event name out of band and the data bodies are `StatusSnapshot` and `{scope}`, so no discriminator property exists; adding one would change the pinned SSE bytes. `spec.md` Implementation Decisions and ticket 04 rule 6 were amended to name `StatusSnapshot` (there is no `StatusEvent`) and to drop the discriminator wording.

Decision 2026-10-04: generated code is excluded from Prettier through `web/.prettierignore` (`src/lib/contract/`), matching user story 21. `gen:contract` does not run prettier, so the committed artifacts are the raw `typed-openapi` output. `jscpd` needs `--ignore "**/lib/contract/**"` for a green gate because the repeated response schemas in `openapi.json` are clones; `--ignore` narrows the scan and does not lower the threshold. Ticket 10 owns the full exclusion set (ESLint, Prettier, knip, jscpd, Vitest coverage) and can move this.

Risk 2026-10-04: the generated module imports `zod`, but `zod` is not declared in `web/package.json` (it is only transitive through knip). Nothing imports the generated module until ticket 08, and declaring `zod` now makes knip fail without an ignore, which `docs/agents/testing.md` forbids. Ticket 08 or 10 must declare `zod ^4` and exclude the contract directory from knip when the client starts importing the schemas.

## Answer

Resolved 2026-10-04.

Landed: `tools/export_contract.py` (imports the real app, dumps with `sort_keys`, writes `web/src/lib/contract/openapi.json`); `pages/contract.py::ContractOpenAPIProvider` (hoists request and response root models into `components.schemas`, documents `/api/events` as `text/event-stream`); `pages/events.py` documents `SseEnvelope`; `src/panel/schemas.py` gains `ReloadEvent` and `SseEnvelope(RootModel[StatusSnapshot | ReloadEvent])`; `Makefile` gains `contract` and runs `$(MAKE) contract` plus `git diff --exit-code -- web/src/lib/contract` before the frontend gates; `web/package.json` gains `gen:contract` (pinned `typed-openapi` 4.1.0 flags); generated `openapi.json` and `panel.gen.ts` are committed.

Tests: `tests/test_contract_export.py` asserts OpenAPI 3.1.0, byte-identical export across two subprocesses with `PYTHONHASHSEED` 0 and 12345, `/api/events` is `text/event-stream`, and the top-level models are hoisted. The generated `panel.gen.ts` type-checks under the full strict flag set (`tsc --noEmit` including `noUncheckedIndexedAccess` and `exactOptionalPropertyTypes`).

Verified: `make check` exit 0 (564 pytest, ruff, ty, vulture, CRAP, jscpd with the contract scope exclusion, ESLint, Prettier, svelte-check, Vitest, knip, 8/8 e2e). Drift gate proven: staged contract `git diff --exit-code` 0, one appended byte 1, `make contract` restores 0. Regeneration is hash-identical across separate processes.

Open for later tickets: fixtures (09); full gate exclusion set and `zod` declaration (08/10).
