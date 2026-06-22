# Review Coverage Completion Gate

The review coverage completion gate is the post-M95 guardrail for the public-safe
reviewer queue. It turns the completed M89-M95 review arc into a deterministic
quality-gate artifact instead of leaving completion as a narrative closeout.

## What It Checks

- The committed review coverage priority plan matches a freshly rebuilt plan.
- Scoped public-safe review coverage is exactly 100.0%.
- Reviewed records, adjudication records, and scored records all match.
- The priority queue is empty.
- No reviewer batch is recommended.
- Every scored source reports `maintain_existing_review_coverage`.
- Scorer reliability reviewed counts still match review coverage counts.

## Deterministic Boundary

The gate reads committed public-safe artifacts only:

- `reports/comparisons/review_coverage_priority_plan.json`
- `reports/comparisons/scorer_reliability_report.json`
- `reports/comparisons/adjudication_regression_snapshot.json`
- `traces/external/adjudication_manifest.json`

It does not rescore traces, change the heuristic scorer, call model providers,
run local models, execute Hermes or OpenClaw, use credentials, access private
evidence, use browser/email tools, touch production systems, or perform external
actions.

## How To Regenerate

```bash
agent-evals review-coverage-completion
```

or:

```bash
python3 src/review_coverage_completion_gate.py
```

The full deterministic quality gate also regenerates and validates the artifact:

```bash
python3 scripts/dev.py check
```

## Interpreting The Result

A passing gate means the current scoped public-safe reviewer queue is exhausted.
It does not mean the scorer is perfect, no future reviews are needed, or the lab
has production safety proof. Future reviewer work should start only after new
public-safe scored traces or a case expansion changes the review scope.
