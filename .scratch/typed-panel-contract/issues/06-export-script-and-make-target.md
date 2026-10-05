# 06: Author the export script and the make target

**Type:** task
**Status:** open
**Blocked by:** 03, 05

## Work

Add the export script that emits the OpenAPI document from the Quart app without a live bot, and the generator step that produces the TypeScript types, the zod validators, and the fixtures from it. Add the `make contract` target and wire the regenerate-then-diff step into `make check`. Commit the generated artifacts under the contract directory.

Done when `make contract` regenerates the artifacts deterministically, `make check` fails when a model edit is not regenerated, and the deterministic-export and validity tests pass.
