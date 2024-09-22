PIP=uv pip

init:
	$(PIP) install -r requirements.txt

start:
	python app.py

test:
	pytest tests

.PHONY: init start test