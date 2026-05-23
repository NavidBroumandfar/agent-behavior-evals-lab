# Adjudication-Aware Reporting

Adjudication-aware reporting summarizes reviewer decisions over existing scored traces without mutating the trace files.

## Reports

`src/adjudication_report.py` writes two Markdown reports:

- `reports/comparisons/adjudication_summary_report.md` summarizes reviewer decision counts, reviewed records by source trace, reviewed records by profile, and record-level decisions.
- `reports/comparisons/adjudicated_aggregate_report.md` separates full heuristic trace results, the reviewed heuristic subset, and the reviewed adjudicated subset.

Run both reports from the repository root:

```bash
python3 src/adjudication_report.py
```

To write only the summary report:

```bash
python3 src/adjudication_report.py --skip-aggregate
```

## Failure Inspection

`src/inspect_failures.py` now loads adjudications by default and annotates failed baseline records with reviewer decisions when a matching adjudication exists.

```bash
python3 src/inspect_failures.py
```

The annotation key is source trace path, run ID, case ID, and profile name. Unreviewed failures remain visible as unreviewed records.

## Regression Snapshot

M11 adds `src/adjudication_regression_check.py` and `reports/comparisons/adjudication_regression_snapshot.json`.

The snapshot records deterministic adjudication aggregates:

- reviewer decision counts
- original vs adjudicated reviewed result counts
- review coverage by source trace
- reviewed records by profile and category
- original and adjudicated failure-mode distributions

Run the check from the repository root:

```bash
python3 src/adjudication_regression_check.py
```

When an intentional fixture change should update the expected counts:

```bash
python3 src/adjudication_regression_check.py --write-snapshot
```

## Boundaries

These reports do not rescore outputs, rewrite trace JSONL, collect new outputs, execute target systems, call provider APIs, use network access, or apply reviewer decisions back to deterministic source traces.

Adjudicated aggregates are report-time views. They must stay separate from heuristic trace results unless a future milestone explicitly adds a controlled trace-rewrite workflow.
