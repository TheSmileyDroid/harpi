#!make

include .env
export $(shell sed 's/=.*//' .env)

start:
	uvicorn app:app

dev:
	uvicorn app:app --reload &
	cd frontend; \
	$(JS_RUNNER) run dev;

types:
	python export.py
	cd frontend; \
	$(JS_RUNNER) run types;
	
.PHONY: start types
