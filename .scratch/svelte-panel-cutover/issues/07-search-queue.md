# 07: Search and queue

**What to build:** Search and queue management work in the new UI, with queue changes arriving live.

**Blocked by:** 06

**Status:** ready-for-agent

- [ ] Typing in search queries the API with debouncing and shows results
- [ ] Queueing a result adds it, and the queue view updates live over SSE
- [ ] Remove and clear work, with confirmation on destructive actions
- [ ] Empty, no-result, and error states are explicit
- [ ] pytest covers the endpoints; a Playwright path covers search, queue, and remove
