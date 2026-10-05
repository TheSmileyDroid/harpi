# 10: Exclude generated artifacts from the quality gates

**Type:** task
**Status:** open
**Blocked by:** 06, 07

## Work

Exclude the contract directory from ESLint, Prettier, knip, jscpd, and Vitest coverage while keeping it inside the type-check include, so a broken artifact still fails `typecheck`. Add the TypeScript globs the strict migration needs to `knip.json` and the ESLint flat config. Confirm the coverage floor still holds with the generated code excluded.

Done when `make check` passes and a deliberately corrupted generated file fails only the type check, not the style gates.
