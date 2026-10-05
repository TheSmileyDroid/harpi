# OpenAPI 3.1 to TypeScript + zod: generator research

Ticket: [01-choose-generator.md](../issues/01-choose-generator.md).

## Verdict

Use **`typed-openapi`** (`--runtime zod`, schemas only). It is the only one of the three that, in one run, emits the TypeScript types *and* the zod validators from a quart-schema OpenAPI 3.1 document, with `$ref` reuse and a real `z.discriminatedUnion`, and whose output type-checks under `noUncheckedIndexedAccess` and `exactOptionalPropertyTypes`. Two conditions apply to how the contract is exported; both are recorded below.

## Method

Primary sources: the projects' own repositories, npm registry metadata, and a live run. The live run used a real Quart app with the repo's pinned `quart-schema==0.23.0` and `pydantic==2.13.4` (`.venv`), dumped the OpenAPI document, then fed it to each generator. Reproduction script: `gen-fixture.py` in this directory. Generated output and type-checks were run in a throwaway directory with TypeScript 5.9.3:

```
tsc --noEmit --target ES2022 --module ESNext --moduleResolution Bundler \
  --lib ES2022,DOM --strict --noUncheckedIndexedAccess --exactOptionalPropertyTypes \
  --noImplicitOverride --noFallthroughCasesInSwitch --isolatedModules \
  --verbatimModuleSyntax <generated-file>
```

Every generated file cited below exited 0.

## quart-schema 0.23.0 emits OpenAPI 3.1.0

Source: `src/quart_schema/openapi.py` in pgjones/quart-schema at tag `0.23.0` hardcodes `"openapi": "3.1.0"`:
<https://github.com/pgjones/quart-schema/blob/0.23.0/src/quart_schema/openapi.py>

The live dump confirmed it (`"openapi": "3.1.0"`) and showed the wire shapes the generators must consume:

- Nested models referenced with `$ref` into `components.schemas` (`Track`, `Layers`).
- Decision: the **top-level** response model is inlined in each response, not registered as a component. `StatusSnapshot` appears inline under every route's `responses.200.content.application/json.schema`.
- Nullable is Pydantic v2 style: `"anyOf": [{"type": "string"}, {"type": "null"}]`, with `"default": null`.
- A tolerated `int | str` request field is `"anyOf": [{"type": "integer"}, {"type": "string"}]`.
- `Literal["status"]` compiles to `"const": "status"` (JSON Schema 2020-12), not `enum`.

The first bullet is the important constraint for the generator choice: **`typed-openapi --schemas-only` emits only component schemas that are reachable from a `$ref`.** With the raw quart-schema document, `StatusSnapshot` was absent from the generated module; the inline response schemas were silently dropped. The same document with `StatusSnapshot` hoisted into `components.schemas` produced it exactly once. The export step (ticket 02/03) must therefore hoist every panel model into `components.schemas` and reference it, which quart-schema supports through its documented `openapi_provider_class` / `build_response_object` override points:
<https://quart-schema.readthedocs.io/en/latest/how_to_guides/index.html>

A second constraint: quart-schema 0.23.0 raises `TypeError: Cannot create schema for ...` when a route's response model is a union (`StatusEvent | ReloadEvent`), because `model_schema` accepts only a class. The SSE union has to reach the document another way (componentized models referenced from the `text/event-stream` schema, or a wrapper/`RootModel`). This is ticket 02's subject; the generator only needs the union to exist as `oneOf` + `discriminator` in the document, which was verified.

## typed-openapi

Repo/README: <https://github.com/astahmer/typed-openapi>. Successor status is stated by the tool it replaces: the `openapi-zod-client` README's first line is "openapi-zod-client is deprecated use typed-openapi instead" (<https://github.com/astahmer/openapi-zod-client>). Latest published version at time of writing: `4.1.0` (<https://registry.npmjs.org/typed-openapi/latest>).

### Exact invocation

Flags, verified:

```sh
typed-openapi contract/openapi.json \
  -o web/src/lib/contract/panel.gen.ts \
  --runtime zod --validation strict --validate-side both \
  --schemas-only --no-runtime-types --no-tree-shake-schemas
```

Equivalent `typed-openapi.config.ts` (auto-loaded from the cwd; JSON also works):

```ts
import { defineConfig } from "typed-openapi";

export default defineConfig({
  input: "./contract/openapi.json",
  output: "./web/src/lib/contract/panel.gen.ts",
  runtime: "zod",
  validation: "strict",
  validateSide: "both",
  schemasOnly: true,
  treeShakeSchemas: false,
  runtimeTypes: false,
  jsdoc: true,
});
```

Caveat found in the 4.1.0 run: setting `treeShakeSchemas: false` or `runtimeTypes: false` in the config file did **not** take effect (the SSE schemas were tree-shaken and a `.types.d.ts` sidecar plus `// @ts-nocheck` was still emitted). The same values passed as CLI flags did. Drive `make contract` with the CLI flags, or pass them alongside `--config`, until that is confirmed fixed.

### Shape of the emitted module

One file, no sidecar, no `@ts-nocheck`, when `--no-runtime-types` is set. Each schema exports a const validator and a type aliased to `z.infer` of it:

```ts
import { z } from "zod";

export type Track = z.infer<typeof Track>;
export const Track = z.strictObject({ id: z.string(), title: z.string(), duration_s: z.number().nullable().default(null), requested_by: z.string().nullable().default(null), thumbnail: z.string().nullable().default(null) });

export type StatusSnapshot = z.infer<typeof StatusSnapshot>;
export const StatusSnapshot = z.strictObject({ connected: z.boolean(), guild_id: z.string().nullable().default(null), now_playing: Track.nullable().default(null), queue: z.array(Track), layers: Layers });

export type PanelEvent = z.infer<typeof PanelEvent>;
export const PanelEvent = z.discriminatedUnion("event", [StatusEvent.extend({ event: z.literal("status") }), ReloadEvent.extend({ event: z.literal("reload") })]);
```

Notes: `additionalProperties` omitted is treated as closed (`z.strictObject`), matching the served shapes; `const` becomes `z.literal`; `oneOf` + `discriminator` becomes `z.discriminatedUnion`. The default (without `--no-runtime-types`) writes the validators to the main module and the public types to a sibling `.types.d.ts`, and puts `// @ts-nocheck` at the top of the validator module, which would defeat user story 22 ("generated files still type-checked"). `--no-runtime-types` avoids both.

### The five evaluation points

- **One run, both types and zod:** yes, `--runtime zod --no-runtime-types`.
- **`$ref` reuse:** yes. Named components are referenced by identifier (`Track`, `Layers`, `Snowflake`), not inlined.
- **Discriminated unions:** yes, `z.discriminatedUnion("event", [...])` from a `oneOf` with `discriminator`.
- **`noUncheckedIndexedAccess` / `exactOptionalPropertyTypes`:** type-checks clean, with and without `skipLibCheck`, on both the hand-built fixture and the real quart-schema-shaped document.
- **OpenAPI 3.1 matching quart-schema 0.23.0:** consumes the real dump (Pydantic `anyOf`-null, `int | str` union, `const`, `$ref` components, `oneOf` + `discriminator`). `--validation strict` keeps formats, bounds, and patterns; `--transform-dates` / `--transform-bigint` are available if the models ever use them.

One extra step is required: `--no-tree-shake-schemas` (or `--schema <regex>`) keeps the SSE event schemas, which are referenced only from the `text/event-stream` response and are otherwise dropped. typed-openapi types a `text/event-stream` response as a raw `ReadableStream` and ignores its schema, so the hand-written SSE dispatcher imports the component schemas (`StatusEvent`, `ReloadEvent`) that this flag preserves.

## orval

Docs: <https://orval.dev/docs/guides/zod> and <https://orval.dev/docs/reference/configuration/output>. Latest: `8.40.0` (<https://registry.npmjs.org/orval/latest>), actively maintained.

### Exact config

```ts
import { defineConfig } from "orval";

export default defineConfig({
  panel: {
    input: { target: "./contract/openapi.json" },
    output: {
      client: "zod",
      mode: "single",
      target: "./web/src/lib/contract/panel.zod.ts",
      override: { zod: { variant: "mini", version: 4, generateReusableSchemas: true } },
    },
  },
});
```

Run with `orval --config orval.config.ts`.

### Shape and the five points

- **One run, both types and zod:** only with `override.zod.generateReusableSchemas: true`. That setting emits both `export const Track = zod.object(...)` and `export type Track = zod.input<typeof Track>` plus `TrackOutput`. Without it, `client: "zod"` emits zod only, inlined per operation.
- **`$ref` reuse:** with `generateReusableSchemas`, named components are reused. Inline response schemas are not: the real document produced `GetGetStatusResponse`, `PostPostConnectResponse`, and a separate `StatusSnapshot`, three structurally identical validators. The componentization fix above removes this, but orval has no `--schemas-only` mode to sidestep the client.
- **Discriminated unions:** **no.** It emits a plain `zod.union([StatusEvent, ReloadEvent])`. There is an open v8 regression, orval-labs/orval#2876: schemas using `oneOf` + `discriminator.propertyName` no longer get the discriminator property in the generated member types (<https://github.com/orval-labs/orval/issues/2876>). The SSE response became `zod.unknown()`.
- **Strict flags:** type-checks clean (the `.input` / `.output` split is exactOptionalPropertyTypes-friendly).
- **OpenAPI 3.1:** parses the real document and handles `anyOf`-null via `union` + `_default`. Historical 3.1 gaps are documented (nullable rendered as `unknown | string`, orval-labs/orval#386; `prefixItems` unsupported until 6.24.0, orval-labs/orval#890).

Orval's zod client is a runtime-validator client, not a schemas-only generator, so it drags in client-generation concerns (operation-named schemas, response wrappers) the spec explicitly does not want ("no caching or data-fetching library", hand-written `createApiClient`).

## openapi-typescript + a zod generator

`openapi-typescript` `7.13.0` (<https://registry.npmjs.org/openapi-typescript/latest>) converts OpenAPI 3.0 and 3.1 to TypeScript types:

```sh
openapi-typescript contract/openapi.json -o web/src/lib/contract/panel.d.ts
```

- **Types quality:** excellent and the best 3.1 fidelity of the three for types. On the real document it emitted `type: ["...", "null"]` as `T | null`, `const` as the literal, `oneOf` + `discriminator` as a union of refs, kept the SSE `text/event-stream` schema typed as `components["schemas"]["PanelEvent"]`, and preserved `$ref` reuse.
- **No zod, by design.** The project ships no validator generator. The API is types-only plus `openapi-fetch`.
- **Companion zod generator:** `openapi-to-zod-schema` `1.3.1` is the common pairing. On the real quart-schema document it mishandled 3.1: `{"type": "null"}` became `z.unknown()` (`duration_s: z.union([z.number(), z.unknown()])`), `const` became `z.unknown()` (`event: z.unknown()`), and `oneOf` became a plain `z.union`. The validators would therefore accept shapes the types forbid. `openapi-zod-client`, the older pairing, is deprecated in favor of typed-openapi.
- **Verdict:** combining the two means two tools with different 3.1 fidelity, a real chance the types and the runtime checks disagree, and a second dependency to maintain. It type-checks cleanly, but it does not meet the "types and checks cannot disagree" requirement (user story 10).

## Recommendation

Pin **`typed-openapi`** for the generator dependency. It is the only evaluated tool that satisfies all of: maintained, one run emits both artifacts, honors `$ref` reuse, emits a true `z.discriminatedUnion`, consumes the exact 3.1 dialect quart-schema 0.23.0 emits, and type-checks under `noUncheckedIndexedAccess` + `exactOptionalPropertyTypes`. Invoke it from `make contract` with the explicit CLI flags above (`--schemas-only --no-runtime-types --no-tree-shake-schemas`), not by relying on the config file's false-valued booleans.

The two implementation constraints this research hands to the tickets that follow:

1. The contract export must hoist the panel's top-level request and response models into `components.schemas` (customize quart-schema's `OpenAPIProvider`), because `typed-openapi --schemas-only` emits only `$ref`-reachable components. Owned by ticket 02 (`quart-schema patterns`) and ticket 03 (`export and gate mechanics`).
2. The SSE union must be a `oneOf` + `discriminator` component referenced from the `text/event-stream` schema, and `make contract` must pass `--no-tree-shake-schemas` so it survives generation. Owned by ticket 02.
