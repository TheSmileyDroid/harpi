# 01: Network-marker harness + single-track smoke test

**What to build:** A real-network pytest marker that keeps the offline suite (`make check`) fast and offline-green, with environment skips for missing outbound network, missing `cookies.txt`, or missing ffmpeg, and library versions printed at run start. On top of it, one smoke test: search "Imagine Dragons - Warriors" through the existing yt-dlp search path, feed the result to the production source seam, read real PCM bytes, and pass the existing stream silence probe.

**Blocked by:** None (can start immediately).

**Status:** ready-for-agent

- [x] `uv run pytest` (as `make check` runs it) never executes the network tests and stays green offline.
- [x] `uv run pytest -m network` runs the suite; it skips cleanly (clear reason each) without network, without `cookies.txt`, or without ffmpeg.
- [x] Test run start prints yt-dlp, yt-dlp-ejs, and ffmpeg versions.
- [x] The smoke test passes on this box with cookies present: search → production source → non-trivial PCM byte flow → non-silence verdict.
- [x] Test output never leaks signed stream URL parameters (uses the existing redaction vocabulary).
