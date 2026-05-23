# Reporting Regression Snapshots

Reporting regression snapshots are deterministic JSON summaries used to catch unexpected reporting drift.

The baseline scorer snapshot lives at `reports/comparisons/baseline_regression_snapshot.json` and is checked by `src/regression_check.py`.

The adjudication snapshot lives at `reports/comparisons/adjudication_regression_snapshot.json` and is checked by `src/adjudication_regression_check.py`.

## Purpose

Snapshots make aggregate changes explicit before they enter the local quality gate. They are especially useful when report Markdown changes are noisy or when reviewer decisions affect multiple downstream tables.

## Updating

Only update a snapshot when the underlying fixture or intended aggregate behavior changed. For adjudications:

```bash
python3 src/adjudication_regression_check.py --write-snapshot
```

The adjudication checker also supports optional quality thresholds:

```bash
python3 src/adjudication_regression_check.py \
  --min-review-coverage 5.0 \
  --max-needs-discussion 2
```

Then run:

```bash
python3 scripts/check_all.py
```

## Boundary

Snapshot checks compare saved local artifacts. They do not collect outputs, call models, execute agents, rescore traces, or apply adjudications back to source traces.
