PIP=uv pip

init:
	$(PIP) install -r requirements.txt

test: init
	pytest tests

start: test
	python app.py

.PHONY: test init