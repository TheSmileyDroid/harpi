# 07: Migrate the panel to strict TypeScript

**Type:** task
**Status:** open
**Blocked by:** None

## Work

Move `web/` to a strict `tsconfig` with `strict`, `noUncheckedIndexedAccess`, `exactOptionalPropertyTypes`, `noImplicitOverride`, `noFallthroughCasesInSwitch`, `isolatedModules`, and `verbatimModuleSyntax`. Big-bang: rename every source file to TypeScript, fix every type error, and drop `allowJs`. Update `svelte-check`, `knip.json`, and the ESLint config globs to match. Keep `make check` green at the end, with no threshold lowered.

Done when `svelte-check` is clean under the strict config, the editor and CI share the config, and the frontend gates pass.
