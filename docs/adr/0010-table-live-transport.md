# ADR 0010: Table live transport over SSE with per-table broadcaster

## Context

The panel already streams one `EventSource` per viewer for music. That
stream is built for a slow read: the sampler polls every 0.5 s, the
response delivers a position frame every 5 s, and each viewer would poll
on its own if it were reused as-is (ADR 0009). A tabletop session needs
token positions at about 10 Hz with five to eight players, fog and turn
changes immediately, and a reconnect that does not lose the scene.

A bench on the real code measured the download at 12.6 KiB/s and 0.75%
of a core for eight viewers on deltas, or 114 KiB/s and 1.0% on full
snapshots. The upload is the expensive side: 600 requests per minute at
10 Hz against an edge limit of 60 per minute, at 0.7 to 1.6 ms of server
time per committed move.

## Decision

Use a dedicated SSE stream per Table, fed by an in-memory broadcaster,
and a batched POST for movement.

- `GET /api/tables/<id>/events` lives in `pages/tables.py`, not in the
  `api` blueprint, whose `after_request` wakes the music sampler on every
  POST.
- `src/panel/table_stream.py` keeps one broadcaster per Table, born with
  the first subscriber and gone with the last, in the shape of the
  sampler. SQLite stays the live truth; the broadcaster only mirrors it
  for framing.
- State travels as absolute deltas: each frame carries `from_stream_rev`
  and `stream_rev`, and the client applies it only when the range
  matches. The broadcaster keeps the last 512 changes per Table, builds
  each subscriber's delta from the revision it already has, and sends a
  full `table.snapshot` on open, on scene change, on explicit scene
  reload and every 5 s as a keyframe. A slow viewer gets a larger delta,
  never a hole; an expired window becomes a snapshot.
- Position frames are coalesced at 10 Hz per Table, not per token, and a
  still table sends only a heartbeat.
- Movement goes through `POST /api/tables/<id>/moves` as a batch with a
  `drag_id` and a `final` flag. The client keeps one request in flight
  per drag, so the connection order is the order of the token. The commit
  happens on drop, with a 5 s safety commit during the drag and a
  `pagehide` commit.
- The move path is the one exception to row CAS: it carries no expected
  revision and never answers 409, because position is a live sample, not
  a concurrent edit. The last drop wins. Structural edits (scene, fog,
  turn, token creation and attributes) keep the CAS and the 409.
- Each viewer gets a state slot that holds only the newest pending
  revision and an append-only event queue of 32. A full queue closes the
  stream. Nothing is dropped silently.
- A dedicated slot pool allows 16 streams per Table and 2 per user,
  separate from the music `STREAM_SLOTS`, and answers 429 with
  `Retry-After: 30`. The table presence is the broadcaster's subscriber set and
  never touches the registry.
- The edge gets its own location for `/api/tables/` at 600 requests per
  minute with a burst of 30. A 429 in the middle of a drag drops the
  client to 1 Hz for 30 s without losing the destination.
- No WebSocket. It buys nothing on the download side, and the upload is
  covered by batching and the edge zone. It returns only if 10 Hz upload
  becomes a hard requirement that the edge cannot satisfy.
- One worker. The broadcaster, `stream_rev`, windows and slots are
  process-local; more than one worker needs a shared bus before anything
  else.

## Consequences

- Eight players dragging at once stay under 1% of a core on the server
  and under 20 KiB/s per viewer.
- A viewer that falls behind converges with a bigger delta instead of
  losing state, and a corrupt client is repaired by the 5 s keyframe.
- Movement is last-writer-wins, which is what a shared table wants: the
  most recent position is the true one.
- A restart drops `stream_rev`; every client adopts the new counter from
  the first snapshot, built from SQLite.
- Panel rolls, sheet changes and table closure need their own events
  because the state frame never carries them.
- Running two workers would silently split the audience and the
  revision counter. The deployment constraint is part of this decision,
  not a note for later.
