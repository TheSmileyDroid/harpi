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

.PHONY: start types dev build
