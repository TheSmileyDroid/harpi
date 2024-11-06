#!make

include .env
export $(shell sed 's/=.*//' .env)

start:
	uvicorn app:app --reload

types:
	python export.py
	cd frontend; \
	$(JS_RUNNER) run types;
	
.PHONY: start types
