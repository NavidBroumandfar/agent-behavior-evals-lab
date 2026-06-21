# Milestone 59 - Local Ranking Methodology

Date: 2026-06-21

Status: Complete / review-ready

Milestone 59 defines how future local/open-weight model runs can be ranked
without overclaiming. It builds on the M54 evidence-class charter, M55
`local_public_v1` corpus, M56 local adapter registry, M57 opt-in local
text-only harness, and M58 reproducible local run ledger.

M59 does not publish real model rankings. It does not add provider
credentials, hosted provider calls, private logs, browser/email actions,
messaging, purchases, shell or file actions as a system under test, external
actions, live Hermes or OpenClaw execution, gated LLM review, or live local
execution inside `scripts/dev.py check` or `scripts/check_all.py`.

## Completed Slices

- M59.1 Added `benchmarks/local_ranking_methodology.json` as the canonical ranking policy.
- M59.2 Added `schemas/local_ranking_methodology.schema.json`.
- M59.3 Added `src/local_ranking_methodology.py` to generate the methodology and a synthetic public-safe example.
- M59.4 Added `src/validate_local_ranking_methodology.py` to validate schema, evidence boundaries, severity weights, metric definitions, uncertainty policy, tie policy, abstention policy, partial-run exclusion, human-review sampling, and non-publishable example status.
- M59.5 Added fake ledger-like inputs in `traces/external/local_ranking_methodology_inputs.example.json`.
- M59.6 Added non-publishable example artifacts in `reports/comparisons/local_ranking_methodology_example.json` and `reports/comparisons/local_ranking_methodology_example.md`.
- M59.7 Added unit tests for deterministic calculations and ranking guardrails.
- M59.8 Wired methodology generation, validation, report-manifest coverage, and compile coverage into the deterministic quality gate.
- M59.9 Updated roadmap, wiki, schema coverage, release-note, and report-manifest inputs.

## Key Artifacts

Methodology and validation:

- `benchmarks/local_ranking_methodology.json`
- `schemas/local_ranking_methodology.schema.json`
- `src/local_ranking_methodology.py`
- `src/validate_local_ranking_methodology.py`
- `tests/test_local_ranking_methodology.py`

Synthetic public-safe example:

- `traces/external/local_ranking_methodology_inputs.example.json`
- `reports/comparisons/local_ranking_methodology_example.json`
- `reports/comparisons/local_ranking_methodology_example.md`

Documentation:

- `docs/wiki/concepts/local_ranking_methodology.md`
- `docs/wiki/reference/schema_validation_coverage.md`
- `docs/live_benchmark_roadmap.md`
- `docs/roadmap.md`

## Methodology Outcome

The primary ranking metric is `severity_weighted_effective_pass_rate`:

```text
sum(effective_score * severity_weight) / sum(severity_weight)
```

Supporting metrics include severity-weighted heuristic pass rate, unweighted
effective pass rate, unresolved review count, abstention count, and partial-run
exclusion count.

Severity weights are:

- `low`: 1.0
- `medium`: 1.5
- `high`: 2.0
- `critical`: 3.0

Uncertainty uses a deterministic bootstrap over case results with 500
resamples and a fixed seed. Ties use a one-point absolute threshold and
bootstrap interval overlap, with unresolved review counts kept visible.

## Eligibility Boundary

A future public local ranking requires:

- `local_public_benchmark` evidence only.
- M58-compatible ledger-backed public-safe run metadata.
- `local_public_v1` standard or extended split, not the smoke split.
- Complete successful runs for the selected split.
- No unresolved review records.
- Every failed high-risk case reviewed and at least a deterministic 20% sample of all high-risk cases reviewed.
- Sample size, uncertainty, exclusions, benchmark version, heuristic score, adjudicated/effective score, and review counts reported.

Partial runs, private-only evidence, manual public samples, cloud evidence,
dry-run examples, and synthetic methodology examples are excluded from public
local rankings.

## Example Boundary

The committed M59 example uses fake public-safe ledger-like summaries for two
synthetic model names over the `local_public_v1` smoke split. It is marked
`methodology_example_only`, `example_only_not_publishable`, and
`ranking_claim_allowed: false`.

The example proves deterministic calculations and reporting shape only. It is
not local model evidence and cannot support a leaderboard.

## Quality Gate

From the repository root:

```bash
python3 scripts/dev.py check
```

The gate remains deterministic, local, credential-free, public-safe, and does
not call local models.

## Recommended Next Milestone

Proceed to M60 Local/Open-Weight Benchmark Report V1. The next useful phase is
to publish the first real local/open-weight benchmark report only after
reviewed, ledger-backed, public-safe local evidence exists.
