# Harpi

Discord bot (music, dice, TTS) with a Svelte panel served as static assets by Quart in one process. Python 3.13, uv, pytest.

## Verify

`make format` then `make check`. Exit 0 means done.

## Read further when it applies

- **Architecture, glossary, code layout** — [docs/agents/architecture.md](docs/agents/architecture.md). Read before touching `src/harpi_lib/`, `src/bot_state.py`, or anything cross-layer.
- **Testing and the gates** — [docs/agents/testing.md](docs/agents/testing.md). Read when writing tests or triaging a failing gate.
- **Panel and API work** — [docs/agents/panel.md](docs/agents/panel.md). Read before editing `pages/`, `web/src/`, or any music surface (commands and panel are one feature on two surfaces).
- **Taste and judgment calls** — [docs/agents/taste.md](docs/agents/taste.md). Read when a design decision could go two ways.
- **Panel design language** — [DESIGN.md](DESIGN.md). Read before editing `web/src/`.
- **Issue tracker** — [docs/agents/issue-tracker.md](docs/agents/issue-tracker.md). Local markdown under `.scratch/<feature-slug>/`.
- **Triage labels** — [docs/agents/triage-labels.md](docs/agents/triage-labels.md). Vocabulary: `needs-triage`, `needs-info`, `ready-for-agent`, `ready-for-human`, `wontfix`.
- **Domain docs** — [docs/agents/domain.md](docs/agents/domain.md). `CONTEXT.md` + `docs/adr/` at the repo root.
