#!/usr/bin/make -f

-include .env
export $(shell sed 's/=.*//' .env 2>/dev/null || true)

.PHONY: dev start lint check mutants tailwind tailwind-watch

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
	uv run ruff check --fix src/ pages/ app.py tools/ tests/
	uv run ruff format src/ pages/ app.py tools/ tests/
	bunx prettier --write ./templates/

check:
	@rm -f .check-failed; \
	uv run ruff check src/ pages/ app.py tools/ tests/ || { touch .check-failed; true; }; \
	uv run ruff format --check src/ pages/ app.py tools/ tests/ || { touch .check-failed; true; }; \
	uv run ty check src/ tests/ pages/ app.py tools/ || { touch .check-failed; true; }; \
	uv run djlint templates/ || { touch .check-failed; true; }; \
	uv run pytest tests/ --cov=src --cov=pages --cov=app --cov-report=json --cov-report=term-missing:skip-covered --cov-fail-under=70 --tb=short -q || { touch .check-failed; true; }; \
	uv run python tools/crap_check.py coverage.json || { touch .check-failed; true; }; \
	bunx jscpd src/ pages/ templates/ --min-tokens 50 --threshold 1 || { touch .check-failed; true; }; \
	bunx prettier --check ./templates/ || { touch .check-failed; true; }; \
	uv run vulture || { touch .check-failed; true; }; \
	if [ -f .check-failed ]; then rm -f .check-failed; exit 1; fi

mutants:
	# mutmut_run.py patches mutmut's mutant naming for this repo's src.*
	# import layout; plain `uv run mutmut run` would never activate mutants.
	uv run python tools/mutmut_run.py run
