#!/usr/bin/make -f

SHELL := /bin/bash
SECURITY_IMAGE ?= harpi:local

-include .env
export $(shell sed 's/=.*//' .env 2>/dev/null || true)

.PHONY: bootstrap dev start build contract lint check check-fast check-network security soak mutants

bootstrap:
	uv sync --upgrade
	( cd web && bun update )

dev:
	@trap 'trap - 0 2 15; kill 0' 0 2 15; \
	bun --cwd=web run dev & \
	uv run python -m src --reload & \
	wait -n

start:
	$(MAKE) build
	uv run python -m src

build:
	( cd web && bun run build )

contract:
	uv run python tools/export_contract.py
	uv run python tools/emit_contract_fixtures.py
	cd web && bun run gen:contract

format:
	uv run ruff check --fix src/ pages/ app.py tools/ tests/
	uv run ruff format src/ pages/ app.py tools/ tests/
	cd web && bun run format

check: contract
	@rm -f .check-failed; \
	( uv run ruff check src/ pages/ app.py tools/ tests/ && \
	  uv run ruff format --check src/ pages/ app.py tools/ tests/ && \
	  uv run ty check src/ tests/ pages/ app.py tools/ && \
	  uv run pytest tests/ --cov=src --cov=pages --cov=app --cov-report=json --cov-report=term-missing:skip-covered --cov-fail-under=70 --tb=short -q -n auto && \
	  uv run python tools/crap_check.py coverage.json && \
	  uv run vulture ) || touch .check-failed & \
	( bunx jscpd@3.5.10 src/ pages/ web/src/ --ignore "**/lib/contract/**" --min-tokens 50 --threshold 1 && \
	  ( cd web && bun run lint && bun run format:check && bun run typecheck && bun run test:coverage && bun run knip ) ) || touch .check-failed & \
	wait; \
	git diff --exit-code -- web/src/lib/contract || touch .check-failed; \
	if [ -f .check-failed ]; then rm -f .check-failed; exit 1; fi; \
	( cd web && bun run e2e ) || exit 1

check-fast:
	@rm -f .check-failed; \
	( uv run ruff check src/ pages/ app.py tools/ tests/ && \
	  uv run ruff format --check src/ pages/ app.py tools/ tests/ && \
	  uv run ty check src/ tests/ pages/ app.py tools/ && \
	  uv run pytest tests/ --tb=short -q -n auto ) || touch .check-failed & \
	( cd web && bun run lint && bun run format:check && bun run typecheck && bun run test ) || touch .check-failed & \
	wait; \
	if [ -f .check-failed ]; then rm -f .check-failed; exit 1; fi

check-network:
	@rm -f .check-failed; \
	uv run pytest -m network -s --tb=short || { touch .check-failed; true; }; \
	if [ -f .check-failed ]; then rm -f .check-failed; exit 1; fi

security:
	@set -e; \
	if command -v gitleaks >/dev/null 2>&1; then \
		gitleaks detect --source . --config .gitleaks.toml --redact --exit-code 1; \
	else \
		echo "gitleaks not installed: secret scan runs in CI"; \
	fi; \
	if command -v osv-scanner >/dev/null 2>&1; then \
		osv-scanner scan source --config osv-scanner.toml --lockfile uv.lock --lockfile web/bun.lock; \
	else \
		echo "osv-scanner not installed: dependency scan runs in CI"; \
	fi; \
	if command -v trivy >/dev/null 2>&1; then \
		if docker image inspect "$(SECURITY_IMAGE)" >/dev/null 2>&1; then \
			trivy image --exit-code 1 --severity HIGH,CRITICAL --ignore-unfixed --ignorefile .trivyignore.yaml "$(SECURITY_IMAGE)"; \
		else \
			echo "no $(SECURITY_IMAGE) image: image scan runs in CI"; \
		fi; \
	else \
		echo "trivy not installed: image scan runs in CI"; \
	fi

soak:
	HARPI_YTDL_DEBUG=1 uv run python -m tools.soak_playback $(SOAK_ARGS)

mutants:
	# mutmut_run.py patches mutmut's mutant naming for this repo's src.*
	# import layout; plain `uv run mutmut run` would never activate mutants.
	uv run python tools/mutmut_run.py run
