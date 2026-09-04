# 04: Upstream-evidence failure report

**What to build:** When a network test fails, its output ends with a structured diagnosis block: which layer failed (extraction / stream / silence), the verbatim error, library versions, and — for known upstream breakage patterns — a link to the matching yt-dlp GitHub issue so the maintainer can see expected-fix timeline instead of guessing.

**Blocked by:** 01: Network-marker harness + single-track smoke test.

**Status:** ready-for-agent

- [x] A simulated extraction failure and a simulated stream failure each produce a diagnosis block naming the failed layer.
- [x] Known upstream breakage patterns match to a linked yt-dlp GitHub issue; unknown patterns report the verbatim error and say no upstream match was found.
- [x] No production code is changed by this ticket — diagnosis lives in the test layer.
- [x] The block never leaks cookies or signed stream URL parameters.
