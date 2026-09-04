# 02: Distinct-videos stability run

**What to build:** The first half of the agreed stability bar: 10 distinct results from the "Imagine Dragons - Warriors" search, each driven through the production source seam (extract → format pick → stream → silence probe), with per-video pass/fail reporting so one bad result is visible among ten.

**Blocked by:** 01: Network-marker harness + single-track smoke test.

**Status:** ready-for-agent

- [x] 10 distinct videos each extract, stream, and pass the silence probe through the production seam.
- [x] The test reports which video failed when it does, using titles/ids (no signed URLs).
- [x] A failure output carries the verbatim yt-dlp/ffmpeg error and the library versions.
- [x] Runs under the network marker; skips cleanly per the 01 harness.
