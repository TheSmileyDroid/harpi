# Harpi

Harpi is a Discord Integrated VTT. Its features includes music playing through voice channels, dice rolling, map making, character sheet manager and campaign managing.

## Verify

`make format` then `make check`. Exit 0 means done. While iterating, `make check-fast` runs the same gates without coverage, CRAP, copy-paste, vulture, knip and Playwright; finish on `make check`.

## Read further when it applies

- **Architecture, glossary, code layout** — [docs/agents/architecture.md](docs/agents/architecture.md). Read before touching `src/harpi_lib/`, `src/bot_state.py`, or anything cross-layer.
- **Testing and the gates** — [docs/agents/testing.md](docs/agents/testing.md). Read when writing tests or triaging a failing gate.
- **Panel and API work** — [docs/agents/panel.md](docs/agents/panel.md). Read before editing `pages/`, `web/src/`, or any music surface (commands and panel are one feature on two surfaces).
- **Taste and judgment calls** — [docs/agents/taste.md](docs/agents/taste.md). Read when a design decision could go two ways.
- **Panel design language** — [DESIGN.md](DESIGN.md). Read before editing `web/src/`.
