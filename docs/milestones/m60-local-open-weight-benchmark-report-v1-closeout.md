# Milestone 60 - Local/Open-Weight Benchmark Report V1

Date: 2026-06-21

Status: Complete / evidence-gated review-ready

Milestone 60 adds the V1 local/open-weight benchmark report surface. The
report is intentionally evidence-gated: it publishes no rankings unless
committed evidence satisfies the M59 methodology.

M60 does not add provider credentials, hosted provider calls, private logs,
browser/email actions, messaging, purchases, shell or file actions as a system
under test, external actions, live Hermes or OpenClaw execution, gated LLM
review, or live local execution inside `scripts/dev.py check` or
`scripts/check_all.py`.

## Completed Slices

- M60.1 Added `schemas/local_benchmark_report.schema.json`.
- M60.2 Added `src/local_benchmark_report.py` to generate the V1 JSON snapshot and Markdown report.
- M60.3 Added `src/validate_local_benchmark_report.py` to validate schema, source hashes, evidence eligibility, no-ranking boundaries, and public-safe assertions.
- M60.4 Added `reports/comparisons/local_open_weight_benchmark_v1.json`.
- M60.5 Added `reports/comparisons/local_open_weight_benchmark_v1.md`.
- M60.6 Added unit tests for no-ranking publication, dry-run ledger exclusion, private-audit rejection, and ranking-claim guardrails.
- M60.7 Wired report generation, validation, report-manifest coverage, and compile coverage into `scripts/check_all.py`.
- M60.8 Updated roadmap, wiki, schema coverage, release-note, and report-manifest inputs.

## Key Artifacts

Report and validation:

- `reports/comparisons/local_open_weight_benchmark_v1.json`
- `reports/comparisons/local_open_weight_benchmark_v1.md`
- `schemas/local_benchmark_report.schema.json`
- `src/local_benchmark_report.py`
- `src/validate_local_benchmark_report.py`
- `tests/test_local_benchmark_report.py`

Documentation:

- `docs/wiki/concepts/local_open_weight_benchmark_report.md`
- `docs/wiki/reference/schema_validation_coverage.md`
- `docs/live_benchmark_roadmap.md`
- `docs/roadmap.md`

## Report Outcome

- Report status: `no_rankings_published`
- Ranking claim allowed: false
- Eligible real local targets: 0
- Excluded evidence entries: 1

The committed M58 dry-run ledger is excluded because it is evaluator-health
evidence, not `local_public_benchmark` evidence; it is a dry-run example; it is
ranking-ineligible; it uses a non-publishable smoke/sample subset; and its
sample size is below the publication minimum.

## Evidence Boundary

The M60 report does not satisfy the real-evidence publication precondition for
a leaderboard because no reviewed live-local, ledger-backed standard-or-
extended split evidence is committed yet.

This is the correct public-safe outcome for the current repository state. The
report exists, but it withholds rankings instead of fabricating model-quality
claims.

## Quality Gate

From the repository root:

```bash
python3 scripts/dev.py check
```

The gate remains deterministic, local, credential-free, public-safe, and does
not call local models.

## Recommended Next Step

Collect reviewed live-local evidence outside the deterministic gate before
publishing rankings, or proceed to M61 Sandboxed Tool Runtime Contract while
keeping the local benchmark report in no-ranking mode until eligible evidence
exists.
