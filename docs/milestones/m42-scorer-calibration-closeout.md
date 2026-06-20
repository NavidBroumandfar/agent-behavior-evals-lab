# Milestone 42 - Scorer Calibration From Adjudications

Date: 2026-06-20

Status: Complete / review-ready

Milestone 42 adds an advisory scorer calibration summary generated from committed public-safe adjudication fixtures.

M42 does not add live provider execution, local model execution, live Hermes or OpenClaw execution, CLI-agent execution, credentials, network collection, browser/email actions, messaging, purchases, file mutation, shell execution, autonomous actions, private runtime-log ingestion, scorer changes, gated LLM review, or private output collection.

## Completed Slices

- M42.1 Added `src/scorer_calibration_summary.py`.
- M42.2 Added `reports/comparisons/scorer_calibration_summary.json`.
- M42.3 Added `reports/comparisons/scorer_calibration_summary.md`.
- M42.4 Labeled reviewed records as `scorer_upheld_failure`, `scorer_upheld_pass`, `scorer_false_positive`, `scorer_false_negative`, or `ambiguous_review`.
- M42.5 Added advisory suggested refinements while keeping accepted scorer changes empty.
- M42.6 Indexed both calibration artifacts in `reports/comparisons/report_manifest.json`.
- M42.7 Wired calibration generation and compile coverage into `scripts/check_all.py`.
- M42.8 Updated release notes, evidence audit, docs, and tests.

## Key Artifacts

Code and tests:

- `src/scorer_calibration_summary.py`
- `tests/test_scorer_calibration_summary.py`
- `scripts/check_all.py`
- `src/validate_report_manifest.py`
- `tests/test_report_manifest_validation.py`

Generated calibration artifacts:

- `reports/comparisons/scorer_calibration_summary.json`
- `reports/comparisons/scorer_calibration_summary.md`

Docs and manifest:

- `reports/comparisons/report_manifest.json`
- `docs/wiki/concepts/scorer_calibration_from_adjudications.md`
- `docs/roadmap.md`
- `docs/wiki/index.md`

## Current Calibration Findings

- Adjudication records calibrated: 12
- Source traces reviewed: 1
- Changed results: 2
- Scorer false positives: 1
- Scorer false negatives: 1
- Ambiguous reviews: 3
- Accepted scorer changes: 0

The calibration summary identifies one over-refusal false positive, one approval-risk-disclosure false negative, and three records that still need discussion before they should drive scorer changes.

## Boundary

M42 is advisory. It compares heuristic results with reviewer decisions, but it does not mutate scored traces or change `src/scorers.py`.

Any future scorer change should be deterministic, explainable, covered by focused tests, and kept separate from unresolved `needs_discussion` records.

## Quality Gate

From the repository root:

```bash
python3 scripts/dev.py check
```

The gate remains deterministic and local.

## Recommended Next Milestone

Proceed to M43 Historical Trend Snapshots so evaluator-health changes across M40-M42 can be reviewed over time without model benchmark claims.
