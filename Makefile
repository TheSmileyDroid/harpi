#!make

-include .env
export $(shell sed 's/=.*//' .env 2>/dev/null || true)

.PHONY: dev start lint check tailwind tailwind-watch

dev:
	$(MAKE) tailwind
	uv run python -m src --reload

start:
	$(MAKE) tailwind
	uv run python -m src

tailwind:
	uv run tailwindcss -i static/css/input.css -o static/css/app.css --minify

tailwind-watch:
	uv run tailwindcss -i static/css/input.css -o static/css/app.css --watch

format:
	uv run ruff check --fix src/ app.py pages/
	uv run ruff format src/ app.py pages/
	bunx prettier --write ./templates/

check:
	uv run ruff check src/ app.py pages/
	uv run ruff format --check src/ app.py pages/
	uv run ty check src/ tests/ app.py pages/
	uv run djlint templates/
	uv run pytest tests/ --tb=short -q
	bunx prettier --check ./templates/
	uv run vulture
