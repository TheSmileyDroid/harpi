# Testing and the gates

`make format` then `make check`: one report, a line per gate, and the detail of
what failed. Raw output lands in `.check/logs/<gate>.log`; `--full` prints
everything and `--only jscpd,pytest` reruns a subset. A gate is green when its
process exited 0 — a parser that cannot read the output never turns red into
green. Two gates also fail on their own output: the contract diff and the
new-clone list.

| Gate | What it proves |
| --- | --- |
| `ruff`, `ruff-format`, `ty` | style, formatting, types |
| `pytest` + coverage | behavior; coverage floor lives in `pyproject.toml` |
| `crap` | complexity × missing coverage stays under 8 |
| `jscpd` | no new clone outside `.jscpd-baseline.json` |
| `vulture` | no dead Python |
| `contract` | the panel contract is regenerated (`make contract`) |
| `eslint`, `prettier`, `svelte-check`, `vitest`, `knip` | the web lane |

`make check-fast` drops the contract diff, coverage, CRAP, copy-paste, vulture
and knip for the inner loop; it is not a merge gate. `make check-e2e` runs
Playwright against one shared backend. Both are required before a PR.
`make check-network` is the deep gate: real YouTube through the production
path (`pytest -m network`), for after a yt-dlp update and when playback breaks.
Skips mean no network, no `cookies.txt` or no ffmpeg — a run where everything
skipped answered nothing.

## The contract

`src/panel/schemas.py` is the source. `make contract` writes
`web/src/lib/contract/{openapi.json,panel.gen.ts,fixtures/fixtures.json}` and
`make check` fails on a diff, so a model change that was not regenerated cannot
merge. pytest locks the document and the SSE names; Vitest parses every fixture
through its generated schema.

## Copy-paste

`jscpd` scans `src/`, `pages/` and `web/src/`. The verdict is a register, not a
percentage: a clone missing from `.jscpd-baseline.json` fails. Each entry
carries its reason; an entry without one counts as new. To accept a clone:
`uv run python tools/check_report.py accept <fingerprint> --reason "why"`.

## Rules

- Backend behavior changes ship with a focused test.
- Tests are deterministic: no network, no sleeps, no timeout-based passes.
- Fakes, not mocks.
- A red gate is fixed or the dead thing it found is deleted. Lowering a
  threshold or adding an ignore is worse than leaving it red and saying so.
