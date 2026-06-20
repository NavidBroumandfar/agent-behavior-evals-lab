# Scorer Calibration From Adjudications

M42 adds an advisory calibration layer that compares deterministic v0 scorer outcomes with committed public-safe adjudication records.

M45 expands the calibration inputs beyond the baseline mock trace by adding public-safe adjudications for selected saved-transcript and normalized adapter-output scored traces.

M46 resolves the remaining ambiguous reviews. After M46, calibration summaries should show zero `ambiguous_review` records unless a future review fixture deliberately reintroduces discussion items.

Generated artifacts:

- `reports/comparisons/scorer_calibration_summary.json`
- `reports/comparisons/scorer_calibration_summary.md`

## Calibration Labels

The calibration report assigns one label to each reviewed adjudication:

- `scorer_upheld_failure`: reviewer upheld a heuristic failure.
- `scorer_upheld_pass`: reviewer upheld a heuristic pass.
- `scorer_false_positive`: heuristic failed a record that review treats as passing.
- `scorer_false_negative`: heuristic passed a record that review treats as failing.
- `ambiguous_review`: reviewer marked the outcome as needing discussion.

## Boundary

The summary reads committed adjudication fixtures and source scored traces only. It does not change `src/scorers.py`, rewrite traces, collect new outputs, call model providers, run local models, execute agents, use browser/email tools, inspect private logs, or perform external actions.

Suggested refinements remain advisory unless a later milestone accepts a deterministic scorer or rubric change with focused tests and regression coverage.
