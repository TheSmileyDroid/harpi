# 04: Seek serialization proven without a clock

**What to build:** The concurrent-seek test proves that a second seek cannot reach the underlying source while the first holds the lock, through causally ordered assertions instead of a timed sleep. The fake underlying source records whether it ever observed a second seek while the first was still blocked; the test asserts that flag is false after both threads join. No production hook is added; the fake is test-local.

**Blocked by:** None (can start immediately).

**Status:** done

- [x] The `time.sleep` and the mid-test fixed-moment assertion are gone.
- [x] The fake source records an overlap flag: set if it sees the second seek position before the first releases.
- [x] The test asserts, after both threads join, that the overlap flag is false.
- [x] The test still proves ordering (first seek completes, then second runs) and final position.
- [x] Core audio touched: `make mutants` was run and survivors triaged (fixed or explained) before calling this done.
- [x] `make format` then `make check` passes.
