.PHONY: check test lint

PYTHON ?= python3

check:
	$(PYTHON) scripts/dev.py check

test:
	$(PYTHON) scripts/dev.py test

lint:
	$(PYTHON) scripts/dev.py lint
