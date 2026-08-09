#!make

-include .env
export $(shell sed 's/=.*//' .env 2>/dev/null || true)

.PHONY: dev start lint check

dev:
	uv run python -m src --reload

start:
	uv run python -m src

format:
	uv run ruff check --fix src/ app.py
	uv run ruff format src/ app.py
	bunx prettier --write ./templates/

check:
	uv run ruff check src/ app.py
	uv run ruff format --check src/ app.py
	uv run ty check src/ tests/ app.py
	uv run vulture
	uv run pytest tests/ --tb=short -q
	bunx prettier --check ./templates/
