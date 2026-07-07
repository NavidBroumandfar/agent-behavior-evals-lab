.PHONY: check test lint quickstart run-baseline report reproduce

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
	$(PYTHON) src/scorer_reliability_report.py

quickstart:
	$(PYTHON) -m pip install ".[dev]"
	$(PYTHON) scripts/dev.py check

# Don't trust the published numbers — regenerate them. Rebuilds the corpus,
# pattern registry, and leaderboard from committed evidence, then runs the
# full deterministic gate. Regeneration tests fail if artifacts drift.
reproduce:
	$(PYTHON) src/local_benchmark_corpus_v2.py
	$(PYTHON) src/pattern_registry.py
	$(PYTHON) src/leaderboard_page.py
	$(PYTHON) src/scorer_judge_calibration.py --aggregate-only || true
	$(PYTHON) scripts/dev.py check
	git diff --stat --exit-code evals/benchmarks/local_public_v2 docs/leaderboard docs/patterns standards
