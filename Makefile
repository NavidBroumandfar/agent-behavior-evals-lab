.PHONY: check test lint quickstart run-baseline report

PYTHON ?= python3

test:
	$(PYTHON) scripts/dev.py test

check:
	$(PYTHON) scripts/dev.py check

lint:
	$(PYTHON) scripts/dev.py lint

run-baseline:
	$(PYTHON) src/run_eval.py

report:
	$(PYTHON) src/report_generator.py
	$(PYTHON) src/comparison_report.py

quickstart:
	$(PYTHON) -m pip install ".[dev]"
	$(PYTHON) scripts/dev.py check
