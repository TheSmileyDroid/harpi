# 07: Migrate the panel to strict TypeScript

**Type:** task
**Status:** resolved
**Blocked by:** None

## Work

Move `web/` to a strict `tsconfig` with `strict`, `noUncheckedIndexedAccess`, `exactOptionalPropertyTypes`, `noImplicitOverride`, `noFallthroughCasesInSwitch`, `isolatedModules`, and `verbatimModuleSyntax`. Big-bang: rename every source file to TypeScript, fix every type error, and drop `allowJs`. Update `svelte-check`, `knip.json`, and the ESLint config globs to match. Keep `make check` green at the end, with no threshold lowered.

Done when `svelte-check` is clean under the strict config, the editor and CI share the config, and the frontend gates pass.

## Comments

Every `web/src/**/*.js` became `.ts`, every `*.test.js` became `*.test.ts`, and `web/e2e/critical-path.spec.js` became `.ts`. The tool entry points stay JavaScript because SvelteKit, Vite, Vitest, and Playwright load them directly: `svelte.config.js`, `vite.config.js`, `vitest.config.js`, `playwright.config.js`. `jsconfig.json` is deleted; `allowJs` appears nowhere.

`web/tsconfig.json` extends `./.svelte-kit/tsconfig.json` and carries the full flag set: `strict`, `noUncheckedIndexedAccess`, `exactOptionalPropertyTypes`, `noImplicitOverride`, `noFallthroughCasesInSwitch`, `isolatedModules`, `verbatimModuleSyntax`. No flag had to be scoped to a path. `exactOptionalPropertyTypes` did not conflict with SvelteKit's generated types, so nothing was dropped or localized. `include` is `src/**/*.ts`, `src/**/*.svelte`, and `e2e/**/*.ts`. The `typecheck` script now passes `--tsconfig ./tsconfig.json`, so editor and CI share one config.

The e2e spec is inside the type-check include, not just renamed. Playwright transpiles TypeScript without checking it, so a renamed spec outside `include` would hide its type errors from the gate; `include` now covers it and the previously invisible errors (a nullable `boundingBox`, `SVGElement | HTMLElement` in `.evaluate`, implicit `any` on the call-log filter) are fixed at the source. Importing `@playwright/test` drags Node-typed Playwright declarations into the program; the declarations reference `Buffer`, `child_process`, `stream`, and `fs` but `@types/node` is not a dependency, and adding it retypes the global timers (the injected `schedule`/`cancel` fakes would stop matching). `skipLibCheck: true` keeps the check on our `.ts`, `.svelte`, and generated `.ts` while ignoring dependency declaration files. It is not a lowered gate threshold; it is the standard scoping for library `.d.ts`.

The wire shape lives in `web/src/lib/types.ts`, hand-written for this ticket. Ticket 08 replaces these with the generated module. `api.ts` exposes `ApiClient = ReturnType<typeof createApiClient>` and every method returns its endpoint type; `$props()` in every component is annotated, so no component prop is `any`.

The generated `web/src/lib/contract/panel.gen.ts` stays inside the type-check include, but is excluded from the other gates. It is ignored by ESLint (`src/lib/contract/` in the flat-config `ignores`), excluded from the knip `project` (`!src/lib/contract/**`) and from Vitest coverage (`exclude`). It imports `zod`, so `zod ^4` is now a direct devDependency; `zod` is listed in knip `ignoreDependencies` because its only consumer is the excluded generated module. Ticket 10 should fold these three exclusions into the formal contract exclusion set.

`knip.json` globs moved to `.ts`: `entry` is `src/routes/**/*.{ts,svelte}` plus `src/app.html`, and `project` is `src/**/*.{ts,svelte}` plus `e2e/**/*.ts` minus the contract directory. ESLint adds `typescript-eslint` (`tseslint.configs.recommended` for `.ts`, `tseslint.parser` inside `<script lang="ts">`) and keeps linting `e2e`.

Dependencies added: `typescript-eslint` and `zod` (both devDependencies). No new lockfile; `bun.lock` is the only lockfile.

Test edits were limited to making the fakes match the wire and satisfying `noUncheckedIndexedAccess`. `api.test.ts` guild and channel ids became strings, matching ADR 0003 and the real server; array reads use non-null assertions (`calls[0]!`). No assertion was weakened, and no behavior changed.

## Answer

Resolved 2026-10-04.

Landed: `web/` is strict TypeScript end to end. Every `web/src/**/*.js` and `web/src/**/*.test.js` became `.ts`, and `web/e2e/critical-path.spec.ts` is now inside the type-check include. `web/jsconfig.json` is gone; `web/tsconfig.json` extends `./.svelte-kit/tsconfig.json` with `strict`, `noUncheckedIndexedAccess`, `exactOptionalPropertyTypes`, `noImplicitOverride`, `noFallthroughCasesInSwitch`, `isolatedModules`, `verbatimModuleSyntax`, and `skipLibCheck`, including `src/**/*.ts`, `src/**/*.svelte`, and `e2e/**/*.ts`. The `typecheck` script points at it. `web/src/lib/types.ts` carries the wire types for this ticket. `web/eslint.config.js` wires `typescript-eslint`; `web/knip.json` and `web/vitest.config.js` globs moved to `.ts`; `zod ^4` is a direct devDependency and the generated module is excluded from ESLint, knip, and Vitest coverage. DevDependencies added: `typescript-eslint`, `zod`.

Verified: `cd web && bun run typecheck` 0 errors and 0 warnings over `src` and `e2e`; `bun run lint` 0; `bun run format:check` 0; `bun run test:coverage` 67 tests, 96.55/85.14/98.96/97 against the unchanged floor of 70; `bun run knip` 0; `bun run e2e` 8/8; `make format` then `make check` exit 0 with the contract regeneration diff clean and every Python gate untouched.

Open for later tickets: ticket 08 replaces `types.ts` with the generated module and parses responses and SSE frames through the generated zod schemas; ticket 10 formalizes the contract exclusion set.


