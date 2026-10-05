# 09: Emit contract fixtures and pin the contract tests

**Type:** task
**Status:** resolved
**Blocked by:** 06

## Work

Emit the frontend test fixtures from the Pydantic models as part of `make contract`. Add a Vitest test that every fixture parses through its generated schema. Add the pytest that asserts the emitted SSE event names equal the registered schema names, and the pytest that the exported document is valid OpenAPI 3.1 and byte-identical across two runs. Replace hand-written fixtures where the generated ones apply.

Done when a model change that is not regenerated fails the gate, and the fixture and event-name parity tests pass.

## Comments

Decision 2026-10-04 (fixture shape): one keyed file, `web/src/lib/contract/fixtures/fixtures.json`, whose keys are the model names and therefore the generated zod schema names. One import, iterate `Object.entries`, direct name-to-schema lookup, no glob or filename parsing. `api.test.ts` and `sse.test.ts` reuse it as `fixtures.StatusSnapshot` / `fixtures.ReloadEvent`.

Decision 2026-10-04 (emitter): `tools/emit_contract_fixtures.py`, invoked from the `contract` target between `export_contract.py` and `gen:contract`. The Python half owns it, like the export. It constructs model instances (the only hand-written part) and writes `model_dump(mode="json")`, so a field change moves the fixture bytes. Deterministic through `json.dumps(indent=2, sort_keys=True)` plus a trailing newline, covered by the existing regenerate-then-diff gate. No new dependency; `polyfactory` was not needed.

Decision 2026-10-04 (fixture set): the top-level wire payloads the frontend fakes use: `Authenticated`, `ChannelList`, `ErrorEnvelope`, `GuildList`, `ReloadEvent`, `SearchResults`, `StatusSnapshot`. Nested models (`Track`, `Layer`, `PlaybackStatus`) are exercised through `StatusSnapshot` and `SearchResults`.

Decision 2026-10-04 (Vitest parse test): `web/src/lib/fixtures.test.ts`, outside `src/lib/contract/` so ESLint and svelte-check see it. It imports the JSON (works because `.svelte-kit/tsconfig.json` sets `moduleResolution: bundler`, which implies `resolveJsonModule`) and the generated namespace, iterates the fixture entries, looks each up through `schemas as Record<string, ZodType>`, and asserts the schema exists and `safeParse` succeeds. It calls the schema directly, not `request()` or `parseFrame`, so it does not reuse the path under test.

Decision 2026-10-04 (SSE parity bridge): a single Python registry `SSE_EVENTS: dict[str, type[BaseModel]]` in `src/panel/schemas.py` maps event name to payload model. `pages/events.py` derives `_EVENT_NAMES` (model to name) and `_frame(model, data)` takes the payload model, so every emitted `event:` line names a registry key. `tests/test_contract_export.py::test_emitted_sse_event_names_match_the_client_schema_map` regex-reads the `SSE_SCHEMAS` object keys in `web/src/lib/sse.ts` and asserts equality with `set(SSE_EVENTS)`. Proven to fail both ways by temporarily renaming the registry key (`status` to `state`) and the TypeScript map key.

Decision 2026-10-04 (replacements): `api.test.ts` `SNAPSHOT`, the session exchange, and the guild/channel list literals; `sse.test.ts` `SNAPSHOT`, the reload literal, and the recovery-frame literal now read generated fixtures. Intentionally invalid frames stay literal. `store.test.ts` keeps its typed domain `snapshot`.

Decision 2026-10-04 (exclusions): no new gate exclusions. `fixtures.json` sits under `src/lib/contract/`, so the ticket 07 ESLint, Prettier, knip, and coverage exclusions already cover it. The Vitest test is outside the contract dir and therefore linted and type-checked. Nothing new to fold into ticket 10.

The Work text above also names the validity and byte-identical export pytests; those landed in ticket 06 and were not duplicated.

Verified 2026-10-04: `make contract` regenerates the fixtures with only `fixtures/` appearing as new, `openapi.json` and `panel.gen.ts` byte-unchanged. Two `PYTHONHASHSEED` runs (0, 12345) produce identical fixture bytes. `make format` then `make check` exit 0: 565 pytest (one new parity test), coverage 95.91% against the floor of 70, Vitest 74/74, svelte-check 0/0, ESLint 0, Prettier clean, knip 0, Playwright 8/8, contract diff clean.

## Answer

Resolved 2026-10-04.

Landed: `tools/emit_contract_fixtures.py` emits one keyed `web/src/lib/contract/fixtures/fixtures.json` from `model_dump(mode="json")`, invoked from `make contract`; `web/src/lib/fixtures.test.ts` proves every fixture parses through its generated schema; `src/panel/schemas.py` gains the `SSE_EVENTS` name-to-model registry, `pages/events.py` derives `_EVENT_NAMES` and emits from it through `_frame(model, data)`; `tests/test_contract_export.py` gains the parity test that reads the `SSE_SCHEMAS` keys from `web/src/lib/sse.ts`; `api.test.ts` and `sse.test.ts` read the generated fixtures where a literal duplicated the wire payload. No new gate exclusion; ticket 10 is unchanged.

Verified: `make format` then `make check` exit 0 (565 pytest, coverage 95.91%, Vitest 74/74, svelte-check 0/0, ESLint 0, Prettier clean, knip 0, Playwright 8/8, contract diff clean); the parity test fails on a rename of either the registry key or the TypeScript map key; fixture bytes are identical across two `PYTHONHASHSEED` runs.
