# 11: Record the contract decision and clean up

**Type:** task
**Status:** open
**Blocked by:** 08, 09, 10

## Work

Write the ADR for the generated-contract approach if it clears the bar (hard to reverse, surprising without context, a real trade-off), and extend or reference ADR 0003 for the `Snowflake` type. Remove the stale vulture `ignore_names` entries in `pyproject.toml` that name an `app.py` `ServerStatusModel` which does not exist. Update `docs/agents/panel.md` and `docs/agents/testing.md` for the contract workflow (`make contract`, the generated directory, the new tests). Run `code-review` and confirm the final `make check` is green with every threshold unchanged.

Done when the docs and ADR reflect the shipped contract, the stale references are gone, and `code-review` reports clean.
