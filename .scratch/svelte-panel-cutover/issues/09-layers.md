# 09: Layers

**What to build:** Layer management works in the new UI, with layer state arriving live.

**Blocked by:** 08

**Status:** done

- [x] Layers can be added, removed, and given a volume
- [x] Removal requires explicit confirmation
- [x] Layer state arrives live and matches server truth
- [x] pytest covers the endpoints; a Playwright path covers adding and removing a layer

## Comments

Schema frozen here, per `spec.md` "Reserved for tickets 06 to 09". All three
endpoints require a selected guild the bot shares AND a live session,
otherwise `404 not_found`, and every one answers `200` with the fresh
`state.status_snapshot`:

- `POST /api/layers` `{"url": str}` -> `actions.add_layer`, answers the fresh
  snapshot. A missing, blank, or non-string url answers `404 not_found`; the
  lookup reuses the queue path's `_mutate_url` helper.
- `POST /api/layers/remove` `{"layer_id": str}` -> `actions.remove_layer`.
  A missing, blank, or non-string id answers `404 not_found`; an id the
  session does not know (the action returns `False`) answers the same `404`.
- `POST /api/layers/volume` `{"layer_id": str, "volume": float}` ->
  `actions.set_layer_volume`. A missing, blank, or non-string id, a
  non-finite or non-number volume, or an unknown id (the action returns
  `False`) answers `404 not_found`.

Each mutation answers exactly `state.status_snapshot`, so the response is
byte-equal to `GET /api/status`. That parity is pinned by a pytest
assertion, like the queue and transport endpoints.

Deliberate decisions:

- `actions.add_layer`'s return value (the created layer id, and the old
  panel's `Virou camada` toast string) is not carried over the JSON
  endpoint; the endpoint ignores the return and answers the snapshot. The
  bot still announces the layer on Discord. This mirrors ticket 07's
  `add_track` warning narrowing.
- "Clear layers" is dropped from the new UI. The old panel's bulk
  `clear_layers` action is not in the spec's reserved contract, so no
  `/api/layers/clear` path exists; per-layer remove remains. `actions.
  clear_layers` stays for the old htmx surface until ticket 10 deletes it.
- Layer state arrives over the existing SSE `status` frames, which already
  carry `playback.layers` (`serialization.layer_data`). No new polling and
  no stream restart: a mutation applies the returned snapshot and toasts,
  and the next frame resyncs the same truth.
- `SearchPanel.svelte` gains a Layer button beside Queue, closing ticket
  07's deferral. It posts the track url to `POST /api/layers`.
- `LayersPanel.svelte` reads `$appStore.playback.layers`; each row shows
  index, thumbnail, title, a perceptual volume slider, and a Remove button.
  Slider position is `volumePosition(layer.volume)` and the sent gain is
  `volumeGain(position)` (`gain = pos²`, ADR 0002); the readout shows the
  linear gain. Remove is gated by `ConfirmDialog.svelte` (Signal Red).
  Explicit no-session and empty states.
- The transport and layer sliders both render a shared
  `VolumeSlider.svelte`, which owns the 300ms `createDebouncer` send and the
  drag lock so an incoming frame never snaps a slider mid-drag. Extracted
  when the layer panel became the second hand-rolled copy of that plumbing.
- `ConfirmDialog.svelte` gained `testid`/`cancelTestid`/`executeTestid`
  props (defaults keep the queue dialog's existing test ids) so the queue
  and layer dialogs can share the component without colliding test ids.
- The layer-row CSS is ported from the old `.layer-row` rule into
  `web/src/app.css`: square corners, no shadows, two-family rule, Signal
  Red only on the destroy button.

Testing:

- pytest (`tests/test_api.py`) covers each endpoint's dispatch and its
  byte-equal-to-status response, invalid and unknown arguments, a live
  session and a shared selection requirement, and the anonymous `401`. The
  layer verbs live on the `ApiSession` subclass with a
  `# ty: ignore[invalid-method-override]` directive, because the shared
  `FakeSession` records calls
  and returns `None`; the subclass mirrors the real session's `bool`/`id`
  returns and mutates `_status.layers`, so `tests/test_music_page.py` stays
  unedited.
- Vitest covers the layer position/gain round trip in
  `web/src/lib/transport.test.js` and the three new client methods in
  `web/src/lib/api.test.js`.
- Playwright (`web/e2e/critical-path.spec.js`) resets the harness, adds a
  layer from a search result, changes its volume, and removes it through its
  own confirm dialog. `web/e2e/backend.py` now mutates `_status.layers` on
  `add_layer`/`remove_layer`/`set_layer_volume`.
