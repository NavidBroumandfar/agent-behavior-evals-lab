# Deterministic Scorer Refinement Triage

M47 adds a deterministic triage layer for scorer and rubric refinement candidates.

Generated artifacts:

- `reports/comparisons/scorer_refinement_triage.json`
- `reports/comparisons/scorer_refinement_triage.md`

Generator:

- `src/scorer_refinement_triage.py`

## What It Decides

The triage reads `reports/comparisons/scorer_calibration_summary.json` and separates candidates into:

- Accepted scorer changes.
- Deferred scorer changes.
- Required follow-up tests.

For M47, no scorer-code changes are accepted. The current false-positive and false-negative candidates each have only one adjudicated source example, so the triage defers them until more focused public-safe evidence and nearby control tests exist.

M48 regenerates the triage after adding broader external fixture review coverage. The added records uphold existing scorer outcomes, so the same scorer-change candidates remain deferred.

M49 adds focused control tests for those candidates and still records a no-change scorer decision. The controls are evidence for a later deterministic change-decision phase, not an automatic scorer update.

## Boundary

The triage does not change `src/scorers.py`, rewrite scored traces, call providers, run local models, execute Hermes or OpenClaw, inspect private logs, use credentials, use networks, or perform external actions.

It is a report-time decision artifact for local deterministic development.

## Future Scorer Changes

Before a future phase accepts a scorer change, it should include:

- At least two public-safe source adjudications for the candidate.
- Focused scorer tests for the target behavior.
- Nearby control tests that protect existing accepted behavior.
- A full `python3 scripts/dev.py check` pass.
