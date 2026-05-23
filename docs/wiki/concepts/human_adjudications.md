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

The committed example fixture is `traces/external/adjudications.example.jsonl`.
