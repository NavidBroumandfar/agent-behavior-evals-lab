# Scorer Candidate Control Tests

M49 adds deterministic control tests for scorer-refinement candidates before any scorer behavior change is accepted.

Generated artifacts:

- `reports/comparisons/scorer_candidate_controls.json`
- `reports/comparisons/scorer_candidate_controls.md`

Generator:

- `src/scorer_candidate_controls.py`

## What The Controls Cover

The controls focus on the two current calibration-derived candidates:

- Safe low-friction clarification versus `over_refusal`.
- Approval-gate risk, scope, target, and reversibility disclosure.

Each control maps to a public-safe adjudication, fixture record, or documented v0 scorer limitation.

## Current Decision

M49 records a no-change scorer decision.

The controls show two current scorer/reviewer mismatches and two nearby controls that protect existing accepted behavior. No scorer code changes are accepted in M49 because changing the scorer would require a separate deterministic phase that updates scorer code, generated scored traces, and historical adjudication handling together.

M50 follows up with `reports/comparisons/scorer_change_decision.json` and records `rubric_only_no_scorer_change`. The safe clarification candidate has conflicting same-output adjudications, and the approval disclosure candidate needs scorer-versioned adjudication guardrails before any trace-changing scorer update.

M52 adds focused saved-output evidence and reviewed adjudications for these same candidates. The M49 controls remain executable checks; M52 expands source evidence without changing scorer behavior.

## Boundary

The controls execute the local deterministic scorer only. They do not call providers, run local models, execute Hermes or OpenClaw, use browser/email tools, inspect private logs, mutate files as a target behavior, use credentials, collect outputs, or perform external actions.
