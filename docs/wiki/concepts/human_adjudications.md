# Human Adjudications

Human adjudications are reviewer records over existing scored traces. They let a reviewer uphold a heuristic score, override it, or flag a case for discussion without mutating the original trace.

## Contract

Adjudication records live in JSONL and are validated by `src/validate_adjudications.py`.

Each record points to a source scored trace through:

- `source_trace_path`
- `run_id`
- `case_id`
- `profile_name`

The validator loads the source trace and confirms that `original_passed`, `original_score`, and `original_failure_modes` match the referenced trace record.

## Decisions

Supported reviewer decisions are:

- `uphold_score`
- `override_pass`
- `override_fail`
- `needs_discussion`

`uphold_score` and `needs_discussion` preserve the original result. `override_pass` must have no adjudicated failure modes. `override_fail` must include adjudicated failure modes.

## Boundary

Adjudications do not rescore outputs or rewrite traces. They are a public-safe review layer that future reports can consume.

The committed example fixtures are:

- `traces/external/adjudications.example.jsonl`
- `traces/external/adjudications.followup.example.jsonl`

M13 indexes committed adjudication fixture families in `traces/external/adjudication_manifest.json`. The manifest records each fixture path, expected record count, source trace paths, quality-gate inclusion status, and public-safe safety assertions.

M14 adds fixture status governance to that manifest. Each fixture records `review_status`, `owner`, `status_notes`, and `last_reviewed_at`; quality-gate fixtures may be `reviewed` or `needs_discussion`, but not `draft` or `blocked`.

M16 adds optional manifest-declared `quality_gate_thresholds` for committed adjudication checks. Manifest-backed regression checks load those thresholds by default, while CLI threshold options remain available for local override experiments.

## Reporting

M10 adds `src/adjudication_report.py`, which writes:

- `reports/comparisons/adjudication_summary_report.md`
- `reports/comparisons/adjudicated_aggregate_report.md`

`src/inspect_failures.py` also annotates failed records with matching reviewer decisions by default. These reports keep heuristic and reviewed results separate.

M11 adds `src/adjudication_regression_check.py`, which checks current adjudication aggregates against `reports/comparisons/adjudication_regression_snapshot.json`. M13 lets that snapshot be built from `traces/external/adjudication_manifest.json` so multiple adjudication fixture families are checked together.
