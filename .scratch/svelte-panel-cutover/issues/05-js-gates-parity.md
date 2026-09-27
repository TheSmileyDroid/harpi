# 05: JS gates at parity

**What to build:** JavaScript quality gates exist at the same strength as the Python ones and run inside `make check`, so every later slice is gated as it lands.

**Blocked by:** 04

**Status:** ready-for-agent

- [ ] Lint, format, type check, frontend coverage floor, duplication check, and dead-code check run inside `make check`
- [ ] Playwright runs inside `make check` and blocks on failure
- [ ] A deliberately introduced lint, type, and test failure each fail the gate, proven by trying it and reverting
- [ ] No existing Python gate is lowered, disabled, or removed to accommodate the frontend
