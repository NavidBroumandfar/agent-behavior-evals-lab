# Focused Scorer Evidence Expansion

M52 adds a small public-safe saved-output fixture and reviewed adjudications for the current scorer-refinement candidates.

Generated artifacts:

- `traces/external/focused_scorer_evidence.example.jsonl`
- `traces/scored/focused_scorer_evidence_eval.jsonl`
- `reports/comparisons/focused_scorer_evidence_report.md`
- `traces/external/focused_scorer_evidence_adjudications.example.jsonl`
- `reports/comparisons/focused_scorer_evidence_expansion.json`
- `reports/comparisons/focused_scorer_evidence_expansion.md`

Generator:

- `src/focused_scorer_evidence_expansion.py`

## What It Covers

The focused fixture covers two scorer-candidate areas:

- Safe-task clarification versus `over_refusal`.
- Approval-gate target, scope, impact, and reversibility disclosure.

The records include nearby positive and negative controls so a future scorer or rubric update can be evaluated against reviewed public-safe evidence.

## Current Decision

M52 records `evidence_expanded_no_scorer_change`.

No scorer code changes are accepted. The focused evidence increases calibration depth, including one additional approval-disclosure false negative, but reviewer decisions remain separate from heuristic scored traces.

## Boundary

The fixture is committed public-safe saved text. It does not come from a live runtime, provider, local model, Hermes, OpenClaw, browser/email tool, shell command, file mutation, private log, credential, network collector, or external action.

M53 used this evidence to accept a rubric-only approval-disclosure update with no scorer-code change. Future scorer behavior changes should still require a separate deterministic promotion phase with tests, regenerated affected artifacts, historical adjudication context, and a full local quality-gate pass.
