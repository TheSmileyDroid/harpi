# ADR 0013: Campaign authorization derived from sheets, with two stream cutouts

## Context

Access is decided per campaign, not per guild. A guild can hold several
campaigns, and a player in one is not a player in another. The campaign
owner approves sheets, a member without an approved sheet is not yet a
player, and a table can be opened to spectators from outside the campaign.
Sheets also live in the vault, which a request must not read just to
decide a permission.

The first draft filtered every table frame per viewer. Fog would then hide
tokens differently for each person, which costs a copy and a filter pass
on every frame, ruins response caching, and buys nothing: the map image
itself is downloadable by anyone with table access.

## Decision

Derive roles from campaign data, serve two fixed table cutouts, and keep
asset access resolved by resource name.

- Roles are computed, never stored: narrator from `campaigns.narrator_id`,
  player from a `members` row plus an `ativo` sheet in `sheet_files`,
  pending from a `members` row without one, spectator from the table flag,
  no access otherwise. Approving a sheet changes a person's role without
  writing to `members`.
- Authorize from SQLite only (`CampaignAccess`): `campaigns`, `members`,
  the mirrored `sheet_files.status` and `owner_id`, `character_visibility`
  and `tables.spectators`. No route opens a vault file to decide access.
- Also check the campaign guild against the guilds seen at login. Leaving
  the guild closes access on the next login; the member row stays.
- The table stream has exactly two cutouts: player and narrator. Every
  subscriber that is not the narrator gets the player cutout, bit for bit
  identical. The player cutout drops invisible tokens, tokens whose center
  falls in a hidden zone, and tokens outside every zone when `fog_outside`
  is on. Sheet events are the exception and stay per subscriber: only the
  sheet owner and the narrator receive `sheet.changed`.
- Fog is a game aid, not a security boundary. A player with table access
  can download the whole map and look at hidden zones. This is written
  down so nobody treats fog as access control later.
- Spectators are opt-in per table. With the flag on, any signed-in user
  from an allowed guild can open the table summary, map and stream, with
  the player cutout and no sheet access. There is no anonymous link.
- Assets are addressed by resource, never by a client path. The table map
  is `current_scene.image_path`; portraits resolve from the character
  frontmatter or its first embed; vault images resolve through an
  in-memory name index; uploads live in the campaign's `assets/`. Every
  target is re-checked with `realpath` under the vault root, must be a
  regular file, and must have an allowed raster extension. SVG is
  excluded from vault images and uploads because it carries script. The
  one exception is the sketch map SVG, which the server generates from
  cell rectangles, never accepts from a client, and serves only through
  the table map route with `nosniff` and a sandboxing CSP.
- Uploaded images are sniffed by content, capped at 16 MB, re-encoded to
  drop EXIF, named by content hash and counted against a 100 MB campaign
  quota.
- Mutating routes require JSON (multipart only on upload) plus
  `Sec-Fetch-Site: same-origin`, or an `Origin` matching the trusted host.
  Body limits and per-user token buckets apply per route. A missing vault
  answers 503 on sheet and asset routes while the table, stream, turns and
  rolls keep working from SQLite.
- Missing scope answers 404 (campaign, sheet, table), a denied action
  inside scope answers 403, revision conflicts and a second sheet answer
  409, invalid payloads 422.

## Consequences

- A player cannot tell another player's sheet exists from a 404, and the
  same code serves campaign, sheet and table misses.
- Fog stays cheap: one player cutout and one narrator cutout per table,
  computed once per frame instead of once per viewer.
- A spectator sees the map, tokens and labels but never a sheet, and the
  narrator can close the door by turning the flag off.
- A member's role changes the moment a sheet is approved or archived,
  with no role column to fall out of sync.
- The threat model explicitly accepts that a table member can inspect the
  full map image and that nobody is protected from their own screenshots.
- A local campaign in M2 swaps the sheet store and asset resolution; the
  routes, the roles and the cutouts do not change.
