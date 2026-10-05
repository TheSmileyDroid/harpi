# 09: Emit contract fixtures and pin the contract tests

**Type:** task
**Status:** open
**Blocked by:** 06

## Work

Emit the frontend test fixtures from the Pydantic models as part of `make contract`. Add a Vitest test that every fixture parses through its generated schema. Add the pytest that asserts the emitted SSE event names equal the registered schema names, and the pytest that the exported document is valid OpenAPI 3.1 and byte-identical across two runs. Replace hand-written fixtures where the generated ones apply.

Done when a model change that is not regenerated fails the gate, and the fixture and event-name parity tests pass.
