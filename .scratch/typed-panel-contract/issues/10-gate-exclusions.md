# 10: Exclude generated artifacts from the quality gates

**Type:** task
**Status:** resolved
**Blocked by:** 06, 07

## Work

Exclude the contract directory from ESLint, Prettier, knip, jscpd, and Vitest coverage while keeping it inside the type-check include, so a broken artifact still fails `typecheck`. Add the TypeScript globs the strict migration needs to `knip.json` and the ESLint flat config. Confirm the coverage floor still holds with the generated code excluded.

Done when `make check` passes and a deliberately corrupted generated file fails only the type check, not the style gates.

## Comments

Decision 2026-10-04 (audit first): the exclusion set already landed piecemeal across tickets 07 and 08, so this ticket was an audit and proof pass, not greenfield config. Every entry was present and working before any edit. No tool config changed.

Per-tool evidence that the skip is real, not a glob that appears to match:

- ESLint: `cd web && bunx eslint src/lib/contract/panel.gen.ts` -> `warning File ignored because of a matching ignore pattern`, exit 0. The flat-config `ignores` entry `src/lib/contract/` covers the directory.
- Prettier: `bunx prettier --check "src/lib/contract/**"` -> all matched files clean, exit 0. The same glob with `--ignore-path /dev/null` flags `openapi.json` and `panel.gen.ts` as unformatted, exit 0 (`[warn]`). The default pass therefore comes from `.prettierignore`, not from the files being formatted.
- knip: `bunx knip --debug` shows the merged ignore list contains `src/lib/contract/**`, from the `!src/lib/contract/**` entry in `project`.
- jscpd: `bunx jscpd web/src/lib/contract --ignore "**/lib/contract/**"` analyzes 0 files; without the flag it finds clones. The full `make check` line without the ignore exits 1, so removing the ignore cannot pass silently.
- Vitest coverage: the coverage table lists no `contract` rows and no `panel.gen`; with the exclude removed by hand the report shows 97.11/89.1/98.97/97.58, still over the floor, so the exclude is behavioral, not cosmetic.
- Type-check: `web/tsconfig.json` `include` is `src/**/*.ts`, which covers the generated `.ts`.

Decision 2026-10-04 (no guard): no single entry can pin the exclusion set. The five tools speak five config formats (`eslint.config.js`, `.prettierignore`, `knip.json`, the `make check` jscpd line, `vitest.config.js`), so a shared constant is not available without inventing a build step. A test that greps each config for the path string asserts config text, not tool behavior, which is the "config-testing for its own sake" this ticket warns against. Two of the five exclusions self-guard anyway: removing Prettier's or jscpd's entry turns `make check` red. Removing ESLint's or coverage's entry does not, but neither hides a broken artifact: `make check` regenerates first and the `git diff --exit-code -- web/src/lib/contract` line then catches any committed artifact that does not match the models. No guard added.

Decision 2026-10-04 (ordering hazard): `make check` runs `make contract` before the style gates, so a corrupted committed `panel.gen.ts` is overwritten before lint, format, knip, coverage, and jscpd run. That is why the corruption is proved against the gates directly, not through `make check`. The regenerate-then-diff line still catches a stale or corrupted committed artifact, because regeneration is deterministic and the diff is against the committed bytes.

Corruption run, exact commands:

- Appended `const corruptedGeneratedArtifact: number = "not a number";` to `web/src/lib/contract/panel.gen.ts` at line 82.
- `cd web && bun run lint` -> exit 0.
- `cd web && bun run format:check` -> exit 0.
- `cd web && bun run knip` -> exit 0.
- `cd web && bun run test:coverage` -> exit 0.
- `bunx jscpd src/ pages/ web/src/ --ignore "**/lib/contract/**" --min-tokens 50 --threshold 1` -> exit 0.
- `cd web && bun run typecheck` -> exit 1: `panel.gen.ts:82:7 Error: Type 'string' is not assignable to type 'number'.`, `svelte-check found 1 error and 0 warnings in 1 file`.
- Restore: `git checkout -- web/src/lib/contract/panel.gen.ts`, then `git status --short web/src/lib/contract` clean. `make contract` then `git diff --exit-code -- web/src/lib/contract` -> exit 0, so regeneration is a byte-identical no-op.

Coverage floor is 70 in `web/vitest.config.js` and untuned. `make check` exit 0 after the restore: 565 pytest, 3 deselected; coverage 96.78 statements / 89.1 branches / 98.97 functions / 97.25 lines; svelte-check 0/0; Vitest 74 passed; ESLint 0; Prettier clean; knip 0; Playwright 8 passed; contract regeneration diff clean.

Changed versus already correct: nothing changed in the tool configs or the generated module; the whole set was already present and is now proven.

## Answer

Resolved 2026-10-04.

Audited the five exclusions and the type-check include: all were already present from tickets 07 and 08, each genuinely skips `web/src/lib/contract/`, and each was proven with a direct tool probe. No config change. No guard: five config formats share no entry, and a config-grep test would assert text, not behavior. The corruption proof stands: a type error in `panel.gen.ts` passes lint, format, knip, coverage, and jscpd, and fails only `typecheck`. `make check` exit 0 with the coverage floor unchanged at 70.
