# Scorer Change Decision

M50 records the deterministic decision on whether M49 scorer candidate controls justify changing the local v0 scorer.

Generated artifacts:

- `reports/comparisons/scorer_change_decision.json`
- `reports/comparisons/scorer_change_decision.md`

Generator:

- `src/scorer_change_decision.py`

## Current Decision

M50 records `rubric_only_no_scorer_change`.

No scorer changes are accepted. The decision preserves existing scored trace behavior and keeps reviewer decisions separate from heuristic scores.

## Why No Scorer Change Was Accepted

The safe-clarification candidate has conflicting adjudicated outcomes for the same strict-profile output text. A broad scorer exception would hide upheld `over_refusal` cases.

The approval-disclosure candidate has a documented false negative, but changing it would require scorer-versioned historical adjudication handling before committed scored traces can safely change.

M51 adds that validation support through optional `historical_scorer_context` records and reports it in `reports/comparisons/scorer_versioning_guardrails.json`.

## Boundary

The decision reads committed public-safe artifacts only. It does not call providers, run local models, execute Hermes or OpenClaw, use browser/email tools, inspect private logs, mutate target files, use credentials, collect outputs, or perform external actions.
