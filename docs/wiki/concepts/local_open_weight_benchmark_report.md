# Local/Open-Weight Benchmark Report

M60 adds the V1 report surface for local/open-weight benchmark results. The
report is evidence-gated: it publishes no ranking unless committed evidence
satisfies the M59 local ranking methodology.

Primary artifacts:

- `reports/comparisons/local_open_weight_benchmark_v1.json`
- `reports/comparisons/local_open_weight_benchmark_v1.md`
- `schemas/local_benchmark_report.schema.json`
- `src/local_benchmark_report.py`
- `src/validate_local_benchmark_report.py`

## Current Report Status

The committed M60 report has `report_status: no_rankings_published` and
`ranking_claim_allowed: false`.

That is intentional. The repository currently has a dry-run M58 ledger example
and synthetic M59 methodology examples, but no reviewed live-local,
ledger-backed standard-or-extended split evidence from real local models.

## Publication Requirements

A future local ranking requires:

- At least two eligible real local/open-weight targets.
- `local_public_benchmark` evidence only.
- M58-compatible ledger entries marked ranking eligible.
- Reviewed live-local outputs with public-safe provenance.
- Standard or extended split coverage, not smoke-only examples.
- M59 metrics, uncertainty, review counts, exclusions, and limitations.

## Boundary

The report generator and validator are deterministic local artifact checks.
They do not run Ollama, local OpenAI-compatible servers, hosted providers,
Hermes, OpenClaw, CLI agents, browser/email tools, shell or file actions as a
system under test, networks, private logs, credentials, gated LLM review, or
external actions.
