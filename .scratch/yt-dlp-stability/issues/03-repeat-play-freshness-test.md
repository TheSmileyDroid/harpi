# 03: Repeat-play freshness test

**What to build:** The second half of the stability bar: 3 consecutive plays of the first "Imagine Dragons - Warriors" search result through the production seam, catching what a one-shot test misses — stream URL expiry between plays and the CDN's spurious 403 on fresh URLs (exercising the real retry budget against the real edge).

**Blocked by:** 01: Network-marker harness + single-track smoke test.

**Status:** ready-for-agent

- [x] 3 consecutive plays of one video each pass the silence probe and deliver PCM bytes.
- [x] The test fails with the probe's error vocabulary (silence / timeout / unplayable) when the CDN rejects a reused or fresh URL beyond the retry budget.
- [x] Failure output includes the play number, verbatim error, and library versions.
- [x] Runs under the network marker; skips cleanly per the 01 harness.
