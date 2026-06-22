# Scorer Reliability Reporting

Scorer v1 reliability reporting adds a deterministic report layer around the
existing heuristic scorer and public-safe adjudications. It improves visibility
without changing scorer behavior.

Generated artifacts:

- `reports/comparisons/scorer_reliability_report.json`
- `reports/comparisons/scorer_reliability_report.md`

Source script:

- `src/scorer_reliability_report.py`

## What It Tracks

The report compares original heuristic outcomes with adjudicated review
outcomes and records:

- scorer false positives and false negatives;
- failure-detector precision, recall, specificity, and accuracy;
- calibration by risk area, category, severity, profile, and fixture;
- disagreement records that need reviewer or rubric attention;
- available reviewer metadata and whether inter-reviewer agreement can be
  estimated from overlapping review targets.

Current committed fixtures have one reviewer decision per target, so the report
does not invent panel agreement. It reports scorer/reviewer agreement and marks
inter-reviewer agreement as unavailable until overlapping reviewer targets
exist.

## Optional Review Contract

`src/scorer_review_contract.py` and `agent-evals scorer-review-contract` define
a non-gated contract stub for future optional scorer review. The contract does
not call providers or local models, does not execute agents, and cannot change
quality-gate results. Writing optional contract files requires
`--acknowledge-non-gated`.

## Boundary

The deterministic heuristic scorer in `src/scorers.py` remains the default
quality-gate scorer. Reliability metrics are advisory reporting signals, not
automatic scorer overrides. The quality gate does not run live provider calls,
local model calls, OpenClaw or Hermes execution, credentials, browser/email
actions, production actions, or external actions.
