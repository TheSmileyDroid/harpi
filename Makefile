PIP=uv pip

init:
	$(PIP) install -r requirements.txt

start:
	python app.py

.PHONY: init