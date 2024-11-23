#!make

include .env
export $(shell sed 's/=.*//' .env)

start: types build
	uvicorn app:app

dev:
	uvicorn app:app --reload &
	cd frontend; \
	$(JS_RUNNER) run dev;

build: types
	cd frontend; \
	$(JS_RUNNER) run build;

types:
	python export.py
	cd frontend; \
	$(JS_RUNNER) run types;

.PHONY: start types dev build
