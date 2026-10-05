# 04: Shape the generated module and the typed client

**Type:** grilling
**Status:** resolved
**Blocked by:** 01, 03

## Question

Given the chosen generator and the exported document, how is the generated module laid out, and how does `createApiClient` consume it?

Decide the file layout under the contract directory (document, generated types and zod, fixtures), how each client method names its endpoint type and which schema it parses with, whether parsing is a shared generic in `request()` or per method, and what happens at runtime when a response or an SSE frame fails validation. The settled intent is fail loud: a parse failure becomes an `ApiError` that reaches the persistent error region, and an unparseable SSE frame does not silently vanish. Confirm or refine that, and decide how the hand-written event-name map is expressed.

This decides the work in "Type and validate the client and SSE against the contract".

## Answer

Settled 2026-10-04.

1. **Layout.** The committed contract lives at `web/src/lib/contract/`: `openapi.json` (the exported document), `panel.gen.ts` (the `typed-openapi` output), and `fixtures/` (JSON emitted from the models). All committed and stale-checked by `make check`.
2. **Schema selection.** `createApiClient` keeps one generic `request()`. Each method passes its response schema, and its request schema where it sends a body, into that call, and the return type is the `z.infer` of the response schema. No hand-maintained endpoint-to-schema table. Because `typed-openapi --schemas-only` emits component schemas only, the client stays hand-written and is typed by the generated component types rather than by generated per-endpoint methods.
3. **Response parse failure.** A zod failure becomes `ApiError` with code `contract_violation` and the HTTP status, routed through the existing `onError` path into the persistent error region unless the call is silent, then thrown. A drifted payload fails loudly instead of reaching a component as `undefined`.
4. **Error bodies.** When the status is not ok, the body is parsed with the generated error-envelope schema. If that parse also fails, the client falls back to the current generic envelope so an unmodeled error still surfaces.
5. **zod.** Pin zod 4, the major `typed-openapi` 4.1.0 targets and whose output was verified to type-check under `noUncheckedIndexedAccess` and `exactOptionalPropertyTypes`.
6. **SSE dispatch.** The frame handler maps the `event:` name to the generated payload schema: `status` to `StatusSnapshot`, `reload` to `ReloadEvent`, parsing only the data body. The name-to-schema map is hand-written because the protocol carries the name out of band, and a pytest pins the emitted event names to the registered schema names. A frame that fails its schema follows rule 3's contract-violation path and is dropped, so a bad frame does not kill the stream.

Amendment 2026-10-04 (ticket 06): the status payload schema is `StatusSnapshot`, not `StatusEvent`. There is no `StatusEvent` model because the status frame's data body is the whole status snapshot. The reload payload is `{scope: string}` (`ReloadEvent`). The generated `SseEnvelope` is `z.union([StatusSnapshot, ReloadEvent])`, not a discriminated union, because the real frames carry no discriminator field and adding one would change the pinned SSE bytes that `tests/test_events.py` locks.

Unblocks ticket 08 once tickets 06 and 07 land.

