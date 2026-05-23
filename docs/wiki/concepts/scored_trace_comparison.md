# Scored Trace Comparison

Scored trace comparison compares two already-scored JSONL trace files by `case_id` and `profile_name`.

The command is:

```bash
python3 src/compare_scored_traces.py \
  --before traces/scored/baseline_mock_run.jsonl \
  --after traces/scored/baseline_mock_run.jsonl \
  --output reports/comparisons/baseline_self_comparison_report.md
```

## What It Reports

The report includes:

- Aggregate pass/fail deltas.
- Shared records whose pass state, score, severity, or failure modes changed.
- New failures.
- Resolved failures.
- Added records.
- Removed records.

## Boundary

The comparison command reads saved scored traces only. It does not rerun evaluation, rescore outputs, collect outputs, run models, or execute agents.

The quality gate runs a baseline self-comparison to prove the command and report path stay deterministic.
