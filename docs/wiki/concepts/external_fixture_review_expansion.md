# External Fixture Review Expansion

M48 expands public-safe adjudication coverage for committed external fixture traces that previously had no reviewer records.

Generated or updated artifacts:

- `traces/external/external_fixture_review_expansion.example.jsonl`
- `traces/external/adjudication_manifest.json`
- `reports/comparisons/adjudication_regression_snapshot.json`
- `reports/comparisons/scorer_calibration_summary.json`
- `reports/comparisons/scorer_refinement_triage.json`

## What Changed

The new fixture adds 22 `uphold_score` adjudications across these already-scored traces:

- `traces/scored/manual_output_eval.jsonl`
- `traces/scored/saved_transcript_replay_eval.jsonl`
- `traces/scored/openclaw_manual_eval.jsonl`
- `traces/scored/dry_run_adapter_output_import.jsonl`
- `traces/scored/openclaw_saved_transcript_pilot_eval.jsonl`

This means each manifest-backed external fixture trace now has at least some committed public-safe review coverage.

## Boundary

The review expansion reads committed scored traces only. It does not collect live outputs, execute providers or local models, run Hermes or OpenClaw, use browser/email tools, mutate files, run shell actions as a target behavior, inspect private logs, or use credentials.

Reviewer decisions remain separate from heuristic scored traces. M48 does not change `src/scorers.py`.

## Follow-Up

Expanded coverage helps calibration, but it does not automatically justify scorer changes. Future scorer or rubric refinements still need focused deterministic tests, nearby controls, and a full local quality-gate pass.
