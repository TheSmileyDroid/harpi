# 03: Decide the export mechanics and gate ordering

**Type:** grilling
**Status:** resolved
**Blocked by:** 01, 02

## Question

How does the OpenAPI document get exported without a live bot, and how do `make contract` and `make check` sequence it?

The export must run inside `make check`, and `app.py` reads settings at import time (`Settings.from_env()` sets the secret key). Options: build a minimal app that mounts only the API blueprints for the export, or supply the environment in the gate, or export from a running instance. Also decide the command split (`make contract` versus a `web` script), whether generation runs before the frontend gates in `make check`, and exactly what the stale check diffs (`git diff --exit-code` over the contract directory). The deterministic-export pytest belongs here.

This decides the work in "Author the export script and the make target".

## Answer

Settled 2026-10-04.

1. **Export source.** `tools/export_contract.py` imports the real app (`from app import app`) and reads `app.extensions["QUART_SCHEMA"].openapi_provider.schema()`. It serializes with `app.json.dumps(schema, indent=2, sort_keys=True)` into `web/src/lib/contract/openapi.json`. Import is offline-safe and needs no bot and no env: `secret_key` may be `None` and `before_serving` never fires on import. Precedent: `tests/test_api.py` already imports the app.
2. **Stale check.** `make contract` regenerates in the tree. `make check` runs `make contract`, then `git diff --exit-code -- web/src/lib/contract`, placed before the frontend lint, format, and typecheck steps. Deterministic generation is the prerequisite.
3. **Command split.** `make contract` runs `uv run python tools/export_contract.py`, then `cd web && bun run gen:contract`, which runs `typed-openapi` and emits the fixtures. The Python half stays in `uv`, the generator stays in the web toolchain.
4. **Checks.** Ordinary pytest cases: the document is valid OpenAPI 3.1, two exports are byte-identical, and the emitted SSE event names equal the registered schema names. No new make target.
5. **Production.** `make build` consumes the committed artifacts and does not run `make contract`, so an image needs neither the Python exporter nor `typed-openapi`.

Constraints carried from the two research tickets:

- The export must place every model into `components.schemas`, because `typed-openapi --schemas-only` emits only `$ref`-reachable components.
- The SSE payload union must be a componentized `oneOf` + `discriminator`, preserved by `--no-tree-shake-schemas`, because quart-schema rejects a bare union response model.
- Error and SSE statuses are documented with `@document_response`, never `@validate_response`.

Unblocks ticket 04 outright and ticket 06 once ticket 05 lands.

