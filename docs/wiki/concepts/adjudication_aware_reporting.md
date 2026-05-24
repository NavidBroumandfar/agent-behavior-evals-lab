# Adjudication-Aware Reporting

Adjudication-aware reporting summarizes reviewer decisions over existing scored traces without mutating the trace files.

## Reports

`src/adjudication_report.py` writes two Markdown reports:

- `reports/comparisons/adjudication_summary_report.md` summarizes reviewer decision counts, reviewed records by source trace, reviewed records by profile, and record-level decisions.
- `reports/comparisons/adjudicated_aggregate_report.md` separates full heuristic trace results, the reviewed heuristic subset, and the reviewed adjudicated subset.

The summary report includes a `Needs Discussion Queue` for adjudications whose reviewer decision is `needs_discussion`.

Run both reports from the repository root:

```bash
python3 src/adjudication_report.py
```

M13 adds manifest-backed reporting for multiple committed adjudication fixture families. With `traces/external/adjudication_manifest.json` present, the no-argument command uses the manifest-backed path; the explicit form is:

```bash
python3 src/adjudication_report.py \
  --manifest traces/external/adjudication_manifest.json
```

When `--manifest` is provided, `--input` is ignored. The summary report includes fixture family counts, fixture paths, quality-gate inclusion status, review status, owner, last-reviewed timestamp, status notes, and reviewer decision counts by fixture.

M14 requires each manifest fixture to include:

- `review_status`: one of `draft`, `reviewed`, `needs_discussion`, or `blocked`
- `owner`
- `status_notes`
- `last_reviewed_at`

Fixtures marked `quality_gate_included: true` cannot use `draft` or `blocked` status.

To write only the summary report:

```bash
python3 src/adjudication_report.py --skip-aggregate
```

## Failure Inspection

`src/inspect_failures.py` loads adjudications by default and annotates failed baseline records with reviewer decisions when a matching adjudication exists.

```bash
python3 src/inspect_failures.py
```

Use the manifest path when failure inspection should include every committed adjudication fixture family:

```bash
python3 src/inspect_failures.py \
  --adjudication-manifest traces/external/adjudication_manifest.json
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
- adjudication fixture review statuses and fixture-level status metadata

Run the check from the repository root:

```bash
python3 src/adjudication_regression_check.py
```

For the manifest-backed multi-fixture snapshot path:

```bash
python3 src/adjudication_regression_check.py \
  --manifest traces/external/adjudication_manifest.json
```

The committed adjudication manifest can declare quality-gate thresholds under `quality_gate_thresholds`. Manifest-backed checks load those thresholds by default:

```bash
python3 src/adjudication_regression_check.py \
  --manifest traces/external/adjudication_manifest.json
```

The manifest threshold block supports:

- `min_review_coverage` for each source trace
- `max_needs_discussion` globally
- `min_profile_review_coverage` by profile
- `min_category_review_coverage` by behavior category
- `max_fixture_needs_discussion` by adjudication fixture family

CLI threshold options remain available for explicit local overrides:

```bash
python3 src/adjudication_regression_check.py \
  --manifest traces/external/adjudication_manifest.json \
  --min-profile-review-coverage generic_assistant=10.0 \
  --min-category-review-coverage approval_gated=10.0 \
  --max-fixture-needs-discussion baseline_reviewed_decisions=2
```

Threshold failures name the exact profile, category, or fixture family that violated the configured limit.

When an intentional fixture change should update the expected counts:

```bash
python3 src/adjudication_regression_check.py \
  --manifest traces/external/adjudication_manifest.json \
  --write-snapshot
```

## Boundaries

These reports do not rescore outputs, rewrite trace JSONL, collect new outputs, execute target systems, call provider APIs, use network access, or apply reviewer decisions back to deterministic source traces.

Adjudicated aggregates are report-time views. They must stay separate from heuristic trace results unless a future milestone explicitly adds a controlled trace-rewrite workflow.
