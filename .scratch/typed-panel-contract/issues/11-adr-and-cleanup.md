# 11: Record the contract decision and clean up

**Type:** task
**Status:** resolved
**Blocked by:** 08, 09, 10

## Work

Write the ADR for the generated-contract approach if it clears the bar (hard to reverse, surprising without context, a real trade-off), and extend or reference ADR 0003 for the `Snowflake` type. Remove the stale vulture `ignore_names` entries in `pyproject.toml` that name an `app.py` `ServerStatusModel` which does not exist. Update `docs/agents/panel.md` and `docs/agents/testing.md` for the contract workflow (`make contract`, the generated directory, the new tests). Run `code-review` and confirm the final `make check` is green with every threshold unchanged.

Done when the docs and ADR reflect the shipped contract, the stale references are gone, and `code-review` reports clean.

## Comments

Decision 2026-10-04 (ADR bar). The generated-contract approach clears the bar, so an ADR is warranted. It is hard to reverse (routes, the client, the tests, and the gate all depend on the generator), surprising without context (committed generated artifacts, an out-of-band SSE name map, in-handler validation instead of a blanket `@validate_request`), and a real trade-off (generated code versus hand types, committed artifacts versus build-time generation, runtime zod validation versus none). Wrote `docs/adr/0004-generated-panel-contract.md` in the existing ADR shape.

Decision 2026-10-04 (ADR 0003). Extended only its Consequences with a bullet: the string-on-the-wire rule now also lives in the `Snowflake` annotated type in `src/panel/schemas.py` and is enforced end to end by the generated contract, not only by tests and the retired hand parsers. The historical bullets are untouched.

Decision 2026-10-04 (docs). `docs/agents/panel.md`: the "One contract" bullet names the Pydantic single source of truth and `make contract`; the Svelte panel paragraph points at the `.ts` files and adds the committed `web/src/lib/contract/` directory, the regenerate-then-diff gate, and the fail-loud `contract_violation` path. `docs/agents/testing.md`: the whole-gate list names the contract gate, and a new "The contract gate" section records `make contract`, the `git diff --exit-code` step, the pytest export tests (validity, determinism, SSE-name parity), and the Vitest fixture-parse test. `CONTEXT.md` gains a **Contract** glossary term. `docs/agents/architecture.md` lists `schemas` in the `src/panel/` seam.

Decision 2026-10-04 (cleanup). The stale vulture `ignore_names` (`app.py` `ServerStatusModel`, `memory_*`) were already removed in ticket 05's commit, so no `pyproject.toml` change here. The only stale `.js` panel paths the effort created were in `docs/agents/panel.md` and `docs/adr/0002-perceptual-volume-slider.md` (`transport.js`); both now name `.ts`. No other stale reference was found.

Decision 2026-10-04 (review). `code-review` ran both axes over `git diff 21f8fde...HEAD`. Standards found three doc gaps, all fixed: the `.js` paths in `panel.md`, `transport.js` in ADR 0002, and the missing `schemas.py` in `architecture.md`. Its other findings are pre-existing or judgement calls: a dead `reduceSse`/`applySse` path in `store.ts` that predates 21f8fde (`+page.svelte` dispatches directly), the generic vulture ignore names added in ticket 05, and duplicated error tails, busy wrappers, and route decorators. None actioned. Spec found three items: the leading-zero snowflake regression (fixed), and two non-defect notes recorded below.

Decision 2026-10-04 (leading-zero fix). `_as_snowflake` returned the stripped digit string, while the retired `_snowflake_field` returned an int. `connect_voice` compares `data.channel_id` against the string set `channel_ids`, so a leading-zero string such as `"010"` that previously resolved to `10` now answered `404 not_found`. `_as_snowflake` now returns `str(int(text))`, restoring the retired behavior and the spec's preservation requirement. New test `tests/test_api.py::test_connect_tolerates_a_leading_zero_digit_string`. The generated contract is unchanged (the field is still a string), so `make contract` stays a byte-identical no-op.

Not fixed, recorded:

- `create_session` reads `payload.get("token")` and validates through `_token_matches` rather than `SessionRequest.model_validate`. The behavior is identical (a missing or non-string token answers the pinned `401 unauthorized`), so there is no defect, and the model still documents the body.
- The error envelope is documented on every route that can return an error. The three read routes (`GET /api/status`, `GET /api/session`, `GET /api/guilds`) declare only `200` because they have no error path, and the session guard's `401` is not documented per route because `before_request` returns it outside response validation. No behavior impact, and documenting the guard per route would touch every decorator and regenerate the contract, beyond the docs and cleanup scope.

## Answer

Resolved 2026-10-04.

ADR: the generated-contract approach cleared the bar, so `docs/adr/0004-generated-panel-contract.md` records the Pydantic single source of truth, quart-schema and OpenAPI 3.1, `typed-openapi`, the committed artifacts with the regenerate-then-diff gate, runtime zod validation on responses and SSE, and the SSE out-of-band name map. ADR 0003 gained a consequence linking the string-on-the-wire rule to the `Snowflake` type and the generated contract.

Docs: `docs/agents/panel.md`, `docs/agents/testing.md`, `CONTEXT.md`, and `docs/agents/architecture.md` updated as above. Cleanup: the stale vulture entries were already gone, and the two stale `.js` panel paths now name `.ts`.

Review: `code-review` Standards and Spec axes over `git diff 21f8fde...HEAD`. Fixed the three doc gaps and the leading-zero snowflake regression. Recorded the two non-defect spec notes.

Verified: `make format` then `make check` exit 0, every threshold unchanged.
