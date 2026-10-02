# 07: Search and queue

**What to build:** Search and queue management work in the new UI, with queue changes arriving live.

**Blocked by:** 06

**Status:** ready-for-agent

- [x] Typing in search queries the API with debouncing and shows results
- [x] Queueing a result adds it, and the queue view updates live over SSE
- [x] Remove and clear work, with confirmation on destructive actions
- [x] Empty, no-result, and error states are explicit
- [x] pytest covers the endpoints; a Playwright path covers search, queue, and remove

## Comments

Schema frozen here, per `spec.md` "Reserved for tickets 06 to 09":

- `POST /api/search` `{"term": str}` -> `200 {"results": [<track>]}` where `<track>` is `serialization.track_data` output, capped at `actions.SEARCH_RESULT_LIMIT`. A blank, missing, or non-string term answers `200 {"results": []}`, and a term with no matches answers `200 {"results": []}`, so the UI has one explicit no-result shape.
- `POST /api/queue` `{"url": str}` -> runs `actions.add_track`, answers `200` with the fresh `state.status_snapshot`.
- `POST /api/queue/remove` `{"url": str}` -> runs `actions.remove_track`, answers `200` with the fresh `state.status_snapshot`.
- `POST /api/queue/clear` -> runs `actions.clear_queue`, answers `200` with the fresh `state.status_snapshot`.
- A queue mutation needs a selected guild the bot shares AND a live session, otherwise `404 not_found`. A missing, blank, or non-string `url` also answers `404 not_found`. Unexpected or network failures flow to the existing `internal_error` 500 envelope.

Deliberate decisions:

- `actions.search` still raises on empty results for the old panel. It delegates to a sibling `actions.search_tracks`, which returns `[]` instead, and both go through `actions._track_list`, so the JSON endpoint gets an explicit no-result shape without editing `pages/music.py` or its tests. `search` keeps the old blank -> `[]` / no matches -> raise split; `search_tracks` answers `[]` for both.
- A pasted http(s) URL in the search box still bypasses the dropdown and goes straight to `POST /api/queue`, matching the old panel's `looks_like_url` path. A plain term goes through `POST /api/search`.
- The search row's LAYER action (adding a track as a layer) is not wired here; it is deferred to ticket 09.
- Each queue mutation answers exactly `state.status_snapshot`, so the response is byte-equal to `GET /api/status`. That parity is pinned by a pytest assertion.
- `actions.add_track`'s all-tracks-skipped warning is not carried over the JSON queue endpoint; the bot still announces the reason on Discord. Deliberate narrowing of parity, recorded here.
- Removing a URL not present is a no-op that still answers the snapshot. Only a missing, blank, or non-string URL is rejected.
- No new app store state: queue contents come from the existing `playback.queue`, and confirm state stays component-local. Two pure helpers were added instead, `createDebouncer` and `formatDuration`, both unit tested.
- Destructive remove and clear are gated by a styled `<dialog>` confirm (Signal Red), not a native `window.confirm`, matching the old panel and DESIGN.md.
- Search debounces at 300ms, matching the old panel's `delay:300ms`. Errors surface in the persistent `errorRegion` plus an inline "search failed" row state, never a toast. Background SSE frames stay silent.
- After a mutation the returned snapshot is applied and a confirmation toast is pushed. Queue changes also arrive over the existing SSE `status` frames, so no stream restart or new polling is needed.
