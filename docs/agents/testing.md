# Testing and the gates

## The whole gate

`make format` then `make check`: ruff, ty, djlint, pytest with coverage, the CRAP gate, copy-paste detection, prettier, vulture. One command, exit 0 means done. Real-network tests are not in it — they live behind the deep gate below.

## Test rules

- Backend behavior changes ship with focused tests for that behavior.
- Tests are deterministic: no network, no sleeps. A test that needs a timeout to pass is wrong.
- Use fakes, not mocks.

## The CRAP gate

Fails any function whose complexity times its missing coverage exceeds 8 (the bar for AI-written code; the human bar is 6). Complex code needs tests, tested code stays simple. Both count.

## Higher-stakes gates

Touching core audio or dice logic: also run `make mutants` and triage the survivors before calling it done.

## When a gate fails

Fix the cause or delete the dead thing it found. Lowering a threshold, adding an ignore, or writing a test that asserts nothing to make it pass are all worse than leaving it red and saying so.

## The deep gate (real network)

Two gates:

- `make check` — fast, offline, always green. Network tests are deselected by default.
- `make check-network` — the deep gate. Real YouTube through the production path: yt-dlp search, extraction, ffmpeg stream, silence probe. `uv run pytest -m network -s --tb=short` (`-s` so the version banner and per-video progress reach the terminal).

Run the deep gate after updating yt-dlp, before deploying, and when playback breaks. Exit 0 means real playback works right now.

Skips are fine: no network, no `cookies.txt`, or no ffmpeg makes the tests skip, not fail. A run where everything skipped means the gate answered nothing — check which condition skipped and why before claiming it green.

Reading a failure: each network test renders a diagnosis block (built by `tests/network_diagnosis.py`):

- `Failed layer` — extraction (yt-dlp could not get the track), stream (ffmpeg could not read the stream), or silence (streamed but empty sound).
- `Verbatim error` — the yt-dlp/probe error text, with signed URL parameters redacted.
- `Library versions` — yt-dlp, yt-dlp-ejs, ffmpeg, so the report is reproducible.
- A linked yt-dlp GitHub issue when the error matches a known upstream breakage pattern; `No upstream match found` otherwise — then check yt-dlp's tracker manually.

First response to new breakage: update yt-dlp, re-run the deep gate. Never diagnose an old version's bugs.
