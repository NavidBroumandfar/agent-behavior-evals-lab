# Adjudicated Aggregate Report

## Data Source

| Field | Value |
| --- | --- |
| Input adjudications | `traces/external/adjudications.example.jsonl` |
| Output report | `reports/comparisons/adjudicated_aggregate_report.md` |
| Source traces reviewed | `traces/scored/baseline_mock_run.jsonl` |
| Reviewed records | 2 |

This report provides an adjudicated view for reviewed records only. It keeps full heuristic trace results, reviewed heuristic results, and reviewed adjudicated results in separate rows.

## Review Coverage By Source Trace

| Source Trace | Source Records | Reviewed Records | Unreviewed Records | Review Coverage |
| --- | ---: | ---: | ---: | ---: |
| `traces/scored/baseline_mock_run.jsonl` | 90 | 2 | 88 | 2.2% |

## Aggregate Result Scopes

| Scope | Total | Passed | Failed | Pass Rate | Notes |
| --- | ---: | ---: | ---: | ---: | --- |
| Full source trace heuristic | 90 | 82 | 8 | 91.1% | All records from source traces referenced by adjudications. |
| Reviewed subset heuristic | 2 | 0 | 2 | 0.0% | Only records with adjudications, using original scorer results. |
| Reviewed subset adjudicated | 2 | 0 | 2 | 0.0% | Only records with adjudications, using reviewer result fields. |

## Result Changes From Review

No reviewed records changed pass/fail result or failure modes.

## Limits

- Unreviewed source-trace records keep their heuristic result and are not implied to be adjudicated.
- Override decisions affect this report only; they do not mutate scored traces.
- This is still a saved-trace reporting layer and does not run live systems or collect new outputs.
