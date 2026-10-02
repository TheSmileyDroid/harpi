# 08: Transport, seek, volume

**What to build:** Transport control with live position, and seek and volume that feel immediate.

**Blocked by:** 07

**Status:** ready-for-agent

- [x] Play, pause, skip, previous, and loop act on the session
- [x] Position updates arrive over SSE and the UI advances without polling
- [x] Seek works by click and by drag, sends absolute seeks, and does not fight incoming updates mid-drag
- [x] Volume changes are debounced and reflected in state
- [x] pytest covers the endpoints; a Playwright path covers a transport interaction with live position

## Comments

Schema frozen here, per `spec.md` "Reserved for tickets 06 to 09". All seven
endpoints require a selected guild the bot shares AND a live session,
otherwise `404 not_found`, and every one answers `200` with the fresh
`state.status_snapshot`:

- `POST /api/playback/pause` -> `actions.pause`, no request body.
- `POST /api/playback/resume` -> `actions.resume`, no request body.
- `POST /api/playback/skip` -> `actions.skip`, no request body.
- `POST /api/playback/previous` -> `actions.previous`, no request body.
- `POST /api/playback/loop` `{"mode": str}` -> `actions.set_loop`. The mode
  is looked up in `session.LOOP_MODE_ALIASES`, so `off`/`track`/`queue` and
  the existing synonyms (`false`/`0`/`no`/`n`, `true`/`1`/`yes`/`y`/`musica`,
  `fila`) all work. A missing, non-string, or unaliased mode answers
  `404 not_found`; the alias table is the single source of truth for what
  counts as valid.
- `POST /api/playback/seek` `{"position": float}` (absolute seconds) ->
  `actions.seek(guild, position)` with `absolute=True`. The endpoint rejects
  a missing, non-number, non-finite, or negative position with
  `404 not_found`, then delegates the duration range check to `actions.seek`
  and maps its `ValueError` to the same `404`, so the panel and the command
  surface share one range rule.
- `POST /api/playback/volume` `{"volume": float}` (linear gain) ->
  `actions.set_volume`; the session clamps to `[0, 1]` (`MAX_VOLUME`), so an
  out-of-range finite number is accepted and clamped. A missing, non-number,
  or non-finite volume answers `404 not_found`.
- Each transport mutation answers exactly `state.status_snapshot`, so the
  response is byte-equal to `GET /api/status`. That parity is pinned by a
  pytest assertion, like the queue endpoints.

Progress unit decision (frozen):

- `SessionStatus.progress` stays **seconds**, matching
  `AudioController.get_queue_position` and the old surface
  (`templates/pages/music.html` computed `elapsed = status.progress`).
  `StatusSurface.svelte` previously multiplied it by 100 and rendered
  seconds as a percentage; that was a bug. The status panel and the
  transport now both render position and duration through
  `formatDuration`, and `serialization.status_data` keeps emitting raw
  seconds on the wire.

Deliberate decisions:

- The transport is a fixed-chrome `TransportBar.svelte` at the bottom edge
  (`bottom: 1.75rem`, above the status strip), styled by porting the real
  `.transport-bar`/`.progress-track`/`.volume-slider` rules from
  `static/css/input.css` into `web/src/app.css`. No new app-store state: the
  bar reads `$appStore.playback` and keeps drag/preview state component-local,
  matching the queue panel.
- Position advances from SSE `status` frames only. There is no client
  polling and no `setInterval` fetch. A local drag preview paints from the
  pointer and, while `seeking` is true, the derived display ratio ignores
  incoming server frames, so a live frame never snaps the preview back
  mid-drag. Seek sends exactly once on pointerup, reusing the old
  script's rule that seek restarts FFmpeg.
- The seek math lives in pure helpers `web/src/lib/transport.js`
  (`pointerRatio`, `seekTarget`), unit-tested in Vitest. `seekTarget` clamps
  a stray ratio and returns 0 for an unknown duration; the component is the
  only DOM reader.
- Volume speaks perceptual position 0-1 and the session speaks linear gain
  (`gain = pos²`, ADR 0002) through `volumeGain`/`volumePosition`. The
  readout shows the linear gain, matching the stored value and `!volume`.
  Sends reuse `createDebouncer` (300ms trailing) and set an `adjustingVolume`
  flag, so the `$effect` that syncs the slider from server truth does nothing
  mid-drag; the slider re-syncs once the send settles.
- Loop cycles `OFF -> TRACK -> QUEUE -> OFF` client-side via pure
  `nextLoopMode`, sends the lowercase alias, and labels the button with the
  current uppercase `loop_mode`.
- Empty state: with no session the bar renders one explicit
  `TRANSPORT // NO SESSION` state and no controls, rather than a disabled
  form.

Testing:

- pytest (`tests/test_api.py`) covers each endpoint's dispatch and its
  byte-equal-to-status response, an invalid mode/position/volume, a live
  session and a shared selection requirement, and the anonymous `401`.
  The transport verbs missing from the shared fake were `pause`, `resume`,
  and `set_loop`; they live on an `ApiSession` subclass in the test file, so
  `tests/test_music_page.py` stays unedited.
- Vitest covers `pointerRatio`, `seekTarget`, `volumeGain`, `volumePosition`,
  and `nextLoopMode` in `web/src/lib/transport.test.js`.
- Playwright (`web/e2e/critical-path.spec.js`) resets the harness, pushes a
  progress frame over SSE, drives pause, clicks the seek bar, and changes
  volume against the fake session that now reflects transport actions
  (`web/e2e/backend.py`).
