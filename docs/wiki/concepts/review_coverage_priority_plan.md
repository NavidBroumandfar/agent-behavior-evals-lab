# Review Coverage Priority Plan

The review coverage priority plan is a deterministic reviewer-work planning
artifact. It reads committed public-safe scored traces, fixture manifests, and
adjudication fixtures, then reports which records already have reviewer coverage
and which unreviewed records should be reviewed first.

The plan does not change scorer behavior. It does not rewrite traces, execute
Hermes or OpenClaw, call providers or local models, inspect private logs, use
credentials, or perform browser, email, production, network, or external
actions.

## What It Prioritizes

- Unreviewed heuristic failures before unreviewed passes.
- Critical and high severity records before lower severity records.
- Records with deterministic failure-mode signals before lower-signal examples.
- Fixture/source coverage gaps that remain public-safe and quality-gate
  eligible.

## How To Use It

Run:

```bash
agent-evals review-coverage-priority
```

The generated JSON and Markdown reports are:

- `reports/comparisons/review_coverage_priority_plan.json`
- `reports/comparisons/review_coverage_priority_plan.md`

Use the priority queue to select the next public-safe adjudication batch. Any
review decisions still need to be committed as adjudication fixtures and kept
separate from deterministic scorer changes unless a later scorer-promotion
artifact explicitly accepts a narrow deterministic change.
