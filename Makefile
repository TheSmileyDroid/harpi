#!make

-include .env
export $(shell sed 's/=.*//' .env 2>/dev/null || true)

.PHONY: dev start lint check

dev:
	uv run python -m src --reload

start:
	uv run python -m src

lint:
	uv run ruff check src/

check:
	uv run ruff check src/
	uv run ruff format --check src/
	uv run vulture src/ app.py --min-confidence 50 --sort-by-size