# Evidence Quality Audit

The evidence quality audit is the M40 reporting layer for understanding what the lab can and cannot currently prove.

It reads committed local artifacts only:

- Eval case JSONL files under `evals/cases/`.
- Baseline and external scored traces under `traces/scored/`.
- Fixture and adjudication manifests under `traces/external/`.
- Adjudication regression snapshots, reporting product summaries, and report-manifest metadata under `reports/comparisons/`.
- Scorer limitation documentation and the roadmap.

The audit produces:

- `reports/comparisons/evidence_quality_audit.json`
- `reports/comparisons/evidence_quality_audit.md`

## What It Shows

The audit inventory summarizes case coverage, scored trace counts, external fixture groups, adjudication coverage, and report-manifest coverage.

The gap report separates findings into:

- Missing fixture coverage.
- Scorer weakness.
- Reporting weakness.

Each gap is tied to source files or fixture groups so follow-up work can be reviewed without private logs or live runtime data.

## Boundary

The audit does not collect new outputs, rescore traces, call providers, run local models, execute Hermes or OpenClaw, inspect private runtime logs, use credentials, use networks, or perform external actions.

It is not a model benchmark, agent leaderboard, or real-world quality claim. It is a deterministic local inventory for deciding what public-safe evidence to add next.
