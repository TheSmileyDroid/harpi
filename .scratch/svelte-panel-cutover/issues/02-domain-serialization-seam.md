# 02: Domain and serialization seam

**What to build:** The data and actions the panel exposes move out of the request handlers into modules that return plain data and perform one domain action per call, so both the current panel and the coming API can call them. Nothing user-visible changes; this is the prefactor that makes the cutover easy.

**Blocked by:** None (can start immediately)

**Status:** ready-for-agent

- [x] Status, guild list, connect, disconnect, search, queue, layer, and transport actions are callable without HTTP or template context
- [x] Existing panel behavior is identical and all current tests pass unedited
- [x] Tests cover each action's success and failure path
