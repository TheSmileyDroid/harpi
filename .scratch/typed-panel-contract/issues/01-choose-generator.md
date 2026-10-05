# 01: Choose and configure the OpenAPI-to-TypeScript generator

**Type:** research
**Status:** resolved
**Blocked by:** None

## Question

Which maintained tool turns an OpenAPI 3.1 document into TypeScript types plus zod validators for this panel, and how is it configured?

Cover `typed-openapi` (the named successor to the deprecated `openapi-zod-client`), `orval`, and `openapi-typescript` combined with a zod generator. For the recommendation, report the exact CLI or config, the shape of the emitted module, whether it can emit both types and zod from one run, how it handles `$ref` reuse and discriminated unions, and whether its output type-checks cleanly under `noUncheckedIndexedAccess` and `exactOptionalPropertyTypes`. Confirm it supports OpenAPI 3.1 as emitted by `quart-schema` 0.23.0.

The finding decides ticket "Shape the generated module and the typed client" and the generator dependency the migration pins.

## Answer

**Recommendation: pin `typed-openapi` (**`--runtime zod`**, schemas only).** It is the only evaluated tool that, in one run, emits the TypeScript types and the zod validators from the quart-schema OpenAPI 3.1 document, honors `$ref` reuse, emits a real `z.discriminatedUnion`, and whose output type-checks under `noUncheckedIndexedAccess` and `exactOptionalPropertyTypes`.

Full report with all primary sources, generated output, and reproduction commands: [research/01-openapi-generator.md](../research/01-openapi-generator.md). Reproduction fixture: [research/gen-fixture.py](../research/gen-fixture.py).

### Exact invocation

```sh
typed-openapi contract/openapi.json \
  -o web/src/lib/contract/panel.gen.ts \
  --runtime zod --validation strict --validate-side both \
  --schemas-only --no-runtime-types --no-tree-shake-schemas
```

`--runtime zod --no-runtime-types` is what makes one file contain both artifacts: each schema emits `export const X = z.strictObject(...)` next to `export type X = z.infer<typeof X>`. Omitting `--no-runtime-types` writes the public types to a sibling `.types.d.ts` and puts `// @ts-nocheck` on the validator module, which would defeat user story 22.

Caveat in 4.1.0: `treeShakeSchemas: false` and `runtimeTypes: false` in `typed-openapi.config.ts` were not honored; the same values as CLI flags were. Drive `make contract` with the explicit flags.

### Evaluation points

- **One run, both types and zod:** yes.
- **`$ref` reuse:** yes; named components referenced by identifier, not inlined.
- **Discriminated unions:** yes; `oneOf` + `discriminator` becomes `z.discriminatedUnion("event", [...])`, and `const` becomes `z.literal`.
- **Strict flags:** type-checks clean (`noUncheckedIndexedAccess`, `exactOptionalPropertyTypes`, no `skipLibCheck`).
- **OpenAPI 3.1 matching quart-schema 0.23.0:** verified against a real dump from the repo's pinned `quart-schema==0.23.0` / `pydantic==2.13.4`; the tag hardcodes `"openapi": "3.1.0"`.

### Why not the others

- **`orval` 8.40.0:** needs `override.zod.generateReusableSchemas: true` to emit types and zod together; emits a plain `zod.union`, not a discriminated union (open v8 regression orval-labs/orval#2876); its SSE response is `zod.unknown()`; and as a client generator it drags in operation-named schemas the spec does not want.
- **`openapi-typescript` 7.13.0 + a zod generator:** openapi-typescript's 3.1 types are the best of the three, but it ships no zod generator, and `openapi-to-zod-schema` 1.3.1 turns `{"type": "null"}` and `const` into `z.unknown()` on the real document. Two tools with different 3.1 fidelity means types and runtime checks can disagree, which user story 10 forbids.

### Constraints this hands to tickets 02 and 03

1. `typed-openapi --schemas-only` emits only component schemas reachable from a `$ref`. quart-schema inlines the top-level response model, so the export must hoist the panel's request and response models into `components.schemas` (quart-schema's `OpenAPIProvider`/`build_response_object` override). Without this, `StatusSnapshot` is absent from the module.
2. quart-schema 0.23.0 raises `TypeError` for a union response model, so the SSE union must become a componentized `oneOf` + `discriminator` referenced from the `text/event-stream` schema, and `make contract` must pass `--no-tree-shake-schemas` to keep it.
