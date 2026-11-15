#!/usr/bin/make -f

SHELL := /bin/bash
SECURITY_IMAGE ?= harpi:local

-include .env
export

.PHONY: bootstrap dev start build contract check check-fast check-e2e check-network security soak

bootstrap:
	uv sync --upgrade
	( cd web && bun update )

dev:
	@trap 'trap - 0 2 15; kill 0' 0 2 15; \
	bun --cwd=web run dev & \
	uv run python -m src --reload & \
	wait -n

start: build
	uv run python -m src

build:
	( cd web && bun run build )

contract:
	@uv run python tools/export_contract.py
	@cd web && bun run gen:contract

format:
	uv run ruff check --fix src/ pages/ app.py tools/ tests/
	uv run ruff format src/ pages/ app.py tools/ tests/
	cd web && bun run format

check: contract
	uv run python tools/check_report.py

check-e2e:
	( cd web && bun run e2e )

check-fast:
	uv run python tools/check_report.py --fast

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
