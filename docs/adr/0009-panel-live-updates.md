# ADR 0009: Live panel updates through one sampler per guild

## Context

The panel learned about changes only from one polling loop per open
`EventSource` (`pages/events.py`): every 0.5 s it rebuilt the whole
`StatusSnapshot`, compared it with the previous one, and yielded a frame
when they differed. Three problems followed.

- The loop had no `try`. A `RuntimeError` or `TimeoutError` from
  `run_on_bot_loop` ended that viewer's response. The client reconnected
  and, if the failure repeated, sat on stale readings with no signal.
- Progress changes on every read, so the comparison almost always
  differed while playing. Every viewer received a ~3.4 kB snapshot twice
  a second, and the time readout advanced in 0.5 s steps.
- Each stream polled independently, so N viewers meant N cross-thread
  hops per tick and no shared place to contain a failure.

Mutation routes returned the new snapshot in their own HTTP response and
never told the stream, so other viewers waited for the next poll.

## Decision

Sample once per guild, publish changed frames to every subscriber, and
split the position out of the snapshot.

- `src/panel/sampler.py` keeps one `GuildSampler` per resolved guild. It
  polls `state.status_snapshot` and the directory every 0.5 s, holds the
  latest sample, and pushes frames into each subscriber's queue.
- The snapshot is compared without `playback.progress`. A change there
  sends the full snapshot; progress alone does not.
- Position travels in its own frame every 5 s, and immediately when it
  jumps by a second or more (seek, skip, pause). The sampler owns the
  value and updates it on every sample; the stream owns the delivery
  tick. The client advances the readout locally from the last sample and
  clamps at the track duration.
- Every `POST` under the API blueprint pokes the sampler after the
  response, so a panel mutation reaches every viewer in the same turn
  instead of on the next poll. The poll stays as reconciliation for
  changes made from Discord.
- Sampler failures are logged once per episode and swallowed. The stream
  keeps the connection alive with a `heartbeat` event and stops sending
  position frames until a sample succeeds.
- A `directory` frame carries the guild list and the selected guild's
  voice channels, published only when they change.
- The presence sample keeps its 5 s cadence and its window narrows from
  30 s to 15 s, so a closed tab ages out of the roster sooner.
- The client watchdog drops a stream that receives nothing, heartbeat
  included, for 15 s. The page marks readings stale when no status,
  position, or directory frame arrives for 15 s, reconnects on
  `visibilitychange` and `online`, and refetches `/api/status` after a
  reconnect.

## Consequences

- A change from another viewer or from Discord lands within one poll
  (0.5 s); a panel mutation lands immediately.
- Traffic while playing drops from ~6.8 kB/s per viewer to a position
  frame every 5 s (about 20 B), plus a heartbeat.
- The time readout is smooth instead of stepping twice a second.
- One failing sample marks readings stale instead of silently freezing
  them, and the connection survives the failure.
- The sampler is process-local state. A future multi-worker deployment
  would need a shared bus; the wire format would survive unchanged.
