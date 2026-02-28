#!make

include .env
export $(shell sed 's/=.*//' .env)

start: types build
	uvicorn app:asgi_app

dev:
	uvicorn app:asgi_app --reload &
	cd ui; \
	$(JS_RUNNER) run dev;

build: types
	cd ui; \
	$(JS_RUNNER) run build;

types:
	python export.py
	cd ui; \
	$(JS_RUNNER) run types;

test:
	uv run pytest tests/ -v --ignore=tests/integration

test-integration:
	uv run uvicorn app:asgi_app --port 5000 & \
	SERVER_PID=$$!; \
	sleep 5; \
	uv run pytest tests/integration/ -v; \
	TEST_EXIT_CODE=$$?; \
	kill $$SERVER_PID || true; \
	exit $$TEST_EXIT_CODE

test-cov:
	uv run pytest tests/ -v --cov=src --cov-report=term-missing --ignore=tests/integration

test-e2e:
	cd ui; \
	bunx playwright test;

test-all: test test-integration

.PHONY: start types dev build test test-integration test-cov test-e2e test-all
