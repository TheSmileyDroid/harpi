# 05: Deep-gate wiring + docs

**What to build:** A `make check-network` target that runs the full real-network suite as the project's deep gate, and a section in the testing agent doc explaining when to run it (after yt-dlp updates, before deploying, when playback breaks) and how to read a failure. `make check` stays exactly as it is: fast, offline, green.

**Blocked by:** 02: Distinct-videos stability run, 03: Repeat-play freshness test, 04: Upstream-evidence failure report.

**Status:** ready-for-agent

- [x] `make check-network` runs every network-marked test and exits nonzero on failure.
- [x] `make check` output and duration are unchanged (network tests excluded by default).
- [x] Testing agent doc documents the two gates and the failure-report format.
- [x] Both gates are green on this box before the ticket closes.
