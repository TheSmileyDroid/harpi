# Decisions

One section per live decision, in the order they were made. Read the section
before changing the area it names. ADRs 0010–0014 were deleted with the VTT
code they described.

## ADR 0002 — Volume is linear gain capped at 1.0

Volume means linear gain on the source, ceiling 1.0 (nothing amplifies). The
panel slider is the only perceptual device: it speaks position 0–1 and posts
`gain = pos²`, because perceived loudness grows with the square of amplitude
and a linear ruler squeezed the everyday range into a sliver. Stored value,
`!volume`, readouts and `MAX_VOLUME` all speak gain, so `!volume 0.08` and a
slider readout of `0.08` name the same state. Rejected: position canonical
everywhere (changes what `!volume` means), pos³ (jumps under the ceiling),
linear (what we escaped). The slider renders `√gain` (`transport.ts`,
`VolumeSlider.svelte`).

## ADR 0003 — Discord ids are strings on the wire

Snowflakes are 64-bit and exceed `Number.MAX_SAFE_INTEGER`, so JSON numbers
lose precision in the browser and every call answered `404 Guild not found`.
Ids travel as strings and the browser keeps them as strings. Rejected:
`BigInt` revivers (`JSON.parse` cannot produce them), a custom codec (too much
machinery for one boundary). Enforced by the `Snowflake` annotated type in
`schemas.py`, so the generated contract carries the shape.

## ADR 0004 — The panel contract is generated from Pydantic

`src/panel/schemas.py` models every request, response and SSE payload;
`quart-schema` serves OpenAPI 3.1 and `typed-openapi` generates the TypeScript
types, zod schemas and fixtures, committed under `web/src/lib/contract/`.
`make check` regenerates and diffs them, so a model edit that was not
regenerated cannot merge, and a drifting server fails where it is called
instead of surfacing `undefined` in a component. Rejected: hand-maintained
types kept honest by tests, generating the Python from TypeScript, generating
at build time, `openapi-zod-client` (deprecated), a blanket
`@validate_request` (changes the pinned error codes), putting the SSE event
name in the document (OpenAPI cannot carry it). The event name lives in
`SSE_EVENTS`/`SSE_SCHEMAS`, with a parity test.

## ADR 0005 — Resolve YouTube JS runtimes by path

YouTube needs an external engine (deno, node, bun, quickjs) to solve signature
challenges. `shutil.which` reads `PATH`, and the systemd unit's `PATH` has none
of the per-user install dirs, so the bot extracted without a solver for days.
Detection now resolves each runtime to an absolute path: `PATH`, then
`HARPI_JS_RUNTIME_DIRS`, then the defaults, and passes `{"path": ...}` to
yt-dlp. Rejected: fixing only the systemd unit (repairs one deployment),
hardcoding a node path (one machine's layout), failing startup (keeps the
cookie-only degraded mode).

## ADR 0006 — yt-dlp works from a copy of the cookie file

`cookies.txt` is logged-in state that cannot be regenerated. yt-dlp rewrites
the jar it is given, which once corrupted it. Each process copies the master
to `cookies.work.txt` in the work directory and points yt-dlp at the copy; a
changed copy is saved under `cookie-backups/` and the master is never written.
The startup log prints the master's sha256. Rejected: backing up before each
run (still lets a bad write become live), mounting read-only only (defense in
depth, not the control), disabling persistence.

## ADR 0007 — Sign the panel in with Discord

A shared `PANEL_TOKEN` identifies no one, must be copied to every person and
locks everyone out on rotation. The panel authenticates with Discord OAuth2
(authorization code + PKCE S256, public client) and admits only accounts that
share a guild with the bot. Rejected: keeping the token as fallback (the weaker
way in becomes the floor), client secret (a stored credential for no gain),
any account (nothing to control), owner only (guild members are confirmed
users). `DISCORD_CLIENT_ID` replaces `PANEL_TOKEN`.

## ADR 0008 — The panel registry is one SQLite file

Per-user selection and the guild roster need to survive a restart and be
queryable by the server, and the deployment target is one process from a repo
clone, so a database service would raise the setup cost. One SQLite file behind
the `Registry` seam (`src/storage/`), migrations in order. The seam keeps the
storage out of the panel modules; the bot never imports the web layer.

## ADR 0009 — One sampler per guild feeds every stream

The first live-update loop polled per open `EventSource`, rebuilt the whole
snapshot twice a second, had no `try` (a cross-loop failure killed the stream),
and mutations never told the stream. Now `GuildSampler` polls once per guild,
compares the snapshot without `progress`, and publishes to every subscriber:
`status` only when something else changed, `position` every 5 s and on a jump
of a second or more, `directory` when it changes, `heartbeat` every 5 s. Every
`POST` pokes the sampler, so a panel mutation lands immediately; the poll stays
as reconciliation for Discord changes. Sampler failures are logged once and
swallowed while the heartbeat keeps the link alive. The client advances the
readout locally and clamps at the duration; it marks readings stale after 15 s
without a status, position or directory frame, and reconnects with backoff.
Consequence: traffic while playing drops from ~6.8 kB/s per viewer to ~20 B
every 5 s. A multi-worker deployment would need a shared bus; the wire format
would survive unchanged.

## ADR 0015 — The VTT surface is removed

Five ADRs built a virtual tabletop inside the panel: live tables, campaign
state in SQLite, vault-synced sheets, per-campaign authorization and the Fate
sheet format. It outgrew the product (20 of 31 panel modules, 43 of 70 routes,
~15k lines of tests) and keeping it half-alive was worse than removing it, so
it was deleted: `pages/campaigns.py`, `pages/tables.py`, the panel modules
behind them, the campaign route tree and its tests. The dice roller stays but
no longer mirrors rolls into the panel. The seven migrations that created the
VTT tables are gone; `0011_drop_vtt.sql` stays, so a database that already ran
them loses those tables on the next boot. Registry, presence, retention,
backup, contract, live stream and OAuth keep working unchanged. Vault files on
disk are untouched. Rebuilding any of it starts from this section and the git
history, not from the deleted code.
