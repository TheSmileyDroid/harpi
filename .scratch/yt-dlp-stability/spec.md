# Spec: yt-dlp + ffmpeg playback stability tests

Status: done

## Problem Statement

The bot plays music from YouTube through yt-dlp and ffmpeg, hosted on a
remote Oracle Linux instance. When YouTube changes something, playback can
break silently: the extraction fails, or a stream URL is served, ffmpeg
reads it, and the result is empty sound. There is no repeatable way to
answer the question "can we, right now, search YouTube, extract a track,
stream it through ffmpeg, and get real, non-silent audio?" — neither on the
dev box nor on the instance. When it breaks, we also lack the evidence to
tell upstream breakage (yt-dlp GitHub issue, expected fix timeline) apart
from a bug in our own code.

## Solution

A suite of real-network tests that drive the production playback path end
to end and assert non-empty, non-silent audio, using the existing stream
probe as the acceptance criterion. The tests degrade gracefully when the
network or `cookies.txt` is absent (skip), but are designed assuming the
cookie file is present. When a test fails, the deliverable is a diagnosis
with the yt-dlp GitHub issue that explains the failure and the expected
fix timeline — not a workaround hack in the production code.

Decisions already made and applied:

- yt-dlp was updated from 2026.7.4 to 2026.8.19 (latest release) before
  writing any tests, so the tests characterize the stack we ship.
- ffmpeg 9.0.1 (system) is the playback decoder under test.

## User Stories

1. As a bot maintainer, I want a test that searches YouTube and streams a
   result through the production source, so that I know music playback
   works before deploying.
2. As a bot maintainer, I want the tests to assert the audio is not
   silent, so that "empty sound" failures are caught before a listener
   reports them.
3. As a bot maintainer, I want the tests to skip cleanly when there is no
   network or no `cookies.txt`, so that offline runs and CI stay green.
4. As a bot maintainer, I want the tests designed assuming cookies are
   present, so that they mirror the hosted deployment's conditions.
5. As a bot maintainer, I want a repeated-play test of the same video, so
   that stream URL expiry and CDN 403 flakiness are caught.
6. As a bot maintainer, I want a distinct-videos test over several search
   results, so that extraction variety (different formats, throttling,
   client rotation) is exercised.
7. As a bot maintainer, I want the tests to use the canonical query
   "Imagine Dragons - Warriors" as the fixture, so that results are
   comparable across runs and machines.
8. As a bot maintainer, I want test failures to point at the failing
   layer (extraction vs. stream vs. silence), so that I can triage in
   minutes instead of hours.
9. As a bot maintainer, when a test fails due to upstream YouTube/yt-dlp
   change, I want the linked yt-dlp GitHub issue in the failure report,
   so that I know whether to wait for a release or act.
10. As a bot maintainer, I want the tests to exercise the same seam the
    bot uses at play time, so that a passing suite means real playback
    works — not just that yt-dlp can download a file.
11. As a bot maintainer, I want the retry behavior of the stream probe
    (spurious 403 on fresh URLs) exercised by the real tests, so that the
    retry budget is validated against the real CDN, not only fakes.
12. As a bot maintainer, I want signed URL parameters redacted in any
    test output, so that logs and failure reports never leak stream
    tokens.
13. As a bot maintainer, I want the library versions recorded in the test
    run output, so that a failure report is reproducible and comparable
    over time.
14. As a bot maintainer, I want updating yt-dlp to be the recommended
    first response to a new breakage, so that we never diagnose an old
    version's bugs.

## Implementation Decisions

- The tests run against the single existing high seam:
  `YoutubeDLSource.from_music_data(YTMusicData)`. This is the seam the bot
  itself uses: it extracts info, reuses search-time formats, falls back to
  a fresh extraction when the reused stream is rejected, validates
  duration, and runs the silence probe before returning a playable
  source. No new seam is introduced.
- The non-empty-sound criterion is the existing
  `stream_probe.probe_stream_audio` (ffmpeg `volumedetect`, 15-second
  window, silence threshold at −60 dB max_volume, 3-attempt retry budget
  with an overall timeout for remote streams). The tests reuse it; they do
  not invent a second silence check.
- As a belt-and-suspenders check, tests read real PCM bytes from the
  `FFmpegPCMAudio` wrapped by the returned source and assert non-trivial
  byte flow, proving audio actually streams and not merely that the probe
  was satisfied.
- Search goes through the existing yt-dlp search path that produces
  `YTMusicData` entries. The fixture query is "Imagine Dragons - Warriors".
  The distinct-videos test uses the first N results of that search; the
  repeat-play test replays the first result.
- Stability bar (agreed): 10 distinct videos, each extracting, streaming,
  and passing the silence probe; plus 3 consecutive plays of one video,
  all passing. Both must hold for "stable".
- Cookie handling: the yt-dlp client config already points at
  `cookies.txt` (gitignored). Tests detect its absence and skip with a
  clear reason; they never create a fake cookie file. No secrets are read
  or logged by the tests.
- When a test fails, the diagnosis loop is: capture the yt-dlp error
  verbatim, search yt-dlp's GitHub issues for the matching breakage
  report, and attach the issue link plus expected-fix assessment to the
  failure report. No production mitigation (client/format tweaks) is
  applied as part of this feature; mitigations are separate decisions
  made with the evidence in hand.
- Library versions (`yt-dlp`, `yt-dlp-ejs`, ffmpeg) are printed at the
  start of the real-network test run.

## Testing Decisions

- Good tests here assert external behavior only: given a query, a playable
  source comes back, reads PCM, and the probe reports non-silence. They
  never assert on yt-dlp internals, format selection details, or process
  spawn mechanics.
- Modules under test: the yt-dlp search path, `YoutubeDLSource.from_music_data`
  (including its reused-vs-fresh stream fallback), and
  `stream_probe.probe_stream_audio` against real CDN streams.
- These are real-network tests, distinct from the existing offline suite.
  They must be selectable (marker) and skippable per-environment: skip
  when there is no outbound network, when `cookies.txt` is absent, or
  when ffmpeg is not installed. The existing offline tests
  (retry-budget tests, ffmpeg-source spawn tests, probe verdict tests)
  remain the fast gate; the real-network suite is the deep gate.
- Prior art in the codebase: the retry-budget tests for the stream probe
  (which already exercise the probe's seams with fakes) and the
  ffmpeg-source tests (which generate real local media fixtures with
  ffmpeg). The new suite reuses the probe's error vocabulary
  (`ProbeSilenceError`, `ProbeTimeoutError`, `ProbeEnvironmentError`) so
  failure semantics are consistent with production.

## Out of Scope

- Full-file downloads of YouTube videos; production streams, it does not
  download, so download behavior is not part of the stability bar.
- Non-YouTube extractors (TTS is local, dice is offline).
- Discord voice connection, opus encoding, and panel wiring — the tests
  stop at the audio source and PCM bytes.
- Any production code change: no format/client option tweaks, no new
  fallback logic. This feature adds tests and, when something breaks, an
  upstream-evidence report.
- Cookie acquisition or renewal automation; `cookies.txt` refresh stays a
  human step.

## Further Notes

- Facts established during scoping: installed yt-dlp was 2026.7.4 and is
  now 2026.8.19 (latest, published 2026-08-19); yt-dlp-ejs 0.8.0; ffmpeg
  n9.0.1. At scoping time no upstream issue documented a total breakage
  of the extract+stream path; open issues were scoped (age-gate format
  availability, embedded player restrictions, subtitles) and are not
  assumed to affect this path until a real test proves otherwise.
- `cookies.txt` on the dev box is fresh (refreshed within the week) and
  mirrors the hosted instance's login approach.
- The reference run target is "Imagine Dragons - Warriors" per the
  maintainer's choice; the suite should accept any query so other tracks
  can be spot-checked later.
