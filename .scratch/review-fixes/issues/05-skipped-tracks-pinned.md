# 05: The skipped-tracks warning is pinned

**What to build:** A test pins the skipped-tracks inference: a session left idle immediately after an add means every queued track was skipped, and the warning appears; a session with genuine playback does not warn. This locks the heuristic against silent rot if play semantics ever change. First step of the ticket is checking whether a test already pins it; if one does, verify it covers both sides (warn and don't-warn) and stop.

**Blocked by:** None (can start immediately).

**Status:** done

## Comments

Existing test `test_add_that_skips_every_track_warns_the_panel` already pins the warn side (tracks skipped → warning fires). Added `test_successful_add_does_not_warn` for the non-warn side (tracks load → no warning). Both are in `tests/test_panel_session_integration.py` and run the real `PlaybackSession` through the panel route.

- [x] Searched the existing panel-to-session integration tests for coverage of the inference; recorded the finding in this file under a `## Comments` heading.
- [x] A test proves the warning fires when a session is idle right after an add.
- [x] A test proves no warning fires while playback is genuinely happening.
- [x] The tests are deterministic: no network, no sleeps.
- [x] `make format` then `make check` passes.
