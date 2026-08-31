# 04: Seek serialization proven without a clock

**What to build:** The concurrent-seek test proves that a second seek cannot reach the underlying source while the first holds the lock, through causally ordered assertions instead of a timed sleep. The fake underlying source records whether it ever observed a second seek while the first was still blocked; the test asserts that flag is false after both threads join. No production hook is added; the fake is test-local.

**Blocked by:** None (can start immediately).

**Status:** ready-for-agent

- [ ] The `time.sleep` and the mid-test fixed-moment assertion are gone.
- [ ] The fake source records an overlap flag: set if it sees the second seek position before the first releases.
- [ ] The test asserts, after both threads join, that the overlap flag is false.
- [ ] The test still proves ordering (first seek completes, then second runs) and final position.
- [ ] Core audio touched: `make mutants` was run and survivors triaged (fixed or explained) before calling this done.
- [ ] `make format` then `make check` passes.
