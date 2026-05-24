# Reporting Regression Snapshots

Reporting regression snapshots are deterministic JSON summaries used to catch unexpected reporting drift.

The baseline scorer snapshot lives at `reports/comparisons/baseline_regression_snapshot.json` and is checked by `src/regression_check.py`.

The adjudication snapshot lives at `reports/comparisons/adjudication_regression_snapshot.json` and is checked by `src/adjudication_regression_check.py`.

The adjudication snapshot includes fixture-level review status metadata from `traces/external/adjudication_manifest.json`, so changes to fixture status, owner, status notes, or last-reviewed timestamps are explicit.

## Purpose

Snapshots make aggregate changes explicit before they enter the local quality gate. They are especially useful when report Markdown changes are noisy or when reviewer decisions affect multiple downstream tables.

## Updating

Only update a snapshot when the underlying fixture or intended aggregate behavior changed. For adjudications:

```bash
python3 src/adjudication_regression_check.py \
  --manifest traces/external/adjudication_manifest.json \
  --write-snapshot
```

The adjudication manifest declares the committed quality thresholds under `quality_gate_thresholds`. The current manifest-backed quality gate uses:

```bash
python3 src/adjudication_regression_check.py \
  --manifest traces/external/adjudication_manifest.json
```

CLI threshold options remain available for explicit local overrides:

```bash
python3 src/adjudication_regression_check.py \
  --manifest traces/external/adjudication_manifest.json \
  --min-profile-review-coverage generic_assistant=10.0 \
  --min-category-review-coverage approval_gated=10.0 \
  --max-fixture-needs-discussion baseline_reviewed_decisions=2
```

These thresholds are local quality-gate policy. Snapshot diffs still track deterministic aggregate changes separately.

Then run:

```bash
python3 scripts/check_all.py
```

## Boundary

Snapshot checks compare saved local artifacts. They do not collect outputs, call models, execute agents, rescore traces, or apply adjudications back to source traces.
