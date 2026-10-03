# Discord IDs as strings over the panel JSON API

Discord snowflakes are 64-bit and exceed JavaScript's `Number.MAX_SAFE_INTEGER`, so a JSON number loses precision as soon as a browser parses it. The panel API used to serialize guild and channel IDs as numbers, and `734174030701264912` arrived in the browser as `734174030701264900`. The channel request then named a guild that does not exist, and every call answered `404 Guild not found`. The panel JSON API now carries guild and channel IDs, including the status snapshot's `guild_id` and `channel_id`, as strings, and the browser keeps them as strings.

## Considered options

- **Keep integers, parse with `BigInt` in the browser**: rejected. `JSON.parse` cannot produce `BigInt`, so every use site would need its own reviver and conversion.
- **A custom bigint JSON codec on both ends**: rejected as too much machinery for one boundary.
- **Strings on the wire**: chosen. It matches Discord's own convention and survives `JSON.parse` with no loss.

## Consequences

- `snowflake()` in `src/panel/serialization.py`, `state.status_snapshot`, and `_snowflake_field` in `pages/api.py` enforce the shape. `_snowflake_field` accepts an int or an ASCII-digit string, so `POST /api/connect` tolerates both.
- `Number()` on a `<select>` value silently reintroduces the rounding. `tests/test_api.py::test_snowflake_ids_stay_exact_over_the_json_api` locks the wire shape, and the Playwright guild-selection test uses a real snowflake and fails if the browser rounds.
