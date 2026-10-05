# 08: Type and validate the client and SSE against the contract

**Type:** task
**Status:** open
**Blocked by:** 04, 06, 07

## Work

Keep `createApiClient`, the store, the toast primitive, and the error region. Each method returns the generated type for its endpoint and parses the response through the endpoint's zod schema. SSE frames parse through their payload schemas through the pinned event-name map. A validation failure surfaces as an `ApiError` into the persistent error region, matching the settled fail-loud intent. Preserve `credentials: "same-origin"` and the `onError` wiring.

Done when no client or SSE code reads `any`, Vitest covers valid and invalid payloads, and the Playwright critical paths still pass.
