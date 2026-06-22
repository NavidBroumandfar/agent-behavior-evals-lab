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

The committed report now has `report_status: published_local_ranking` and
`ranking_claim_allowed: true`.

M83 unlocked the report from two eligible reviewed live-local extended ledgers:
`llama3.2:latest` from M79 and `mistral:latest` from M82. The dry-run M58
ledger remains excluded, and the report still does not support cloud-model
rankings, hosted-provider comparisons, production-safety proof, private-audit
proof, or third-party output-regeneration claims.

## Publication Requirements

A local ranking requires:

- At least two eligible real local/open-weight targets.
- `local_public_benchmark` evidence only.
- M58-compatible ledger entries marked ranking eligible.
- Reviewed live-local outputs with public-safe provenance.
- Standard or extended split coverage, not smoke-only examples.
- M59 metrics, uncertainty, review counts, exclusions, and limitations.

M84 adds the public-safe reproducibility packet for the current published
ranking at `docs/milestones/m84-public-safe-reproducibility-packet-closeout.md`.
M86 adds the claim-review checklist at
`traces/external/claim_review_checklist.example.json`; it keeps release wording
bounded to the local/open-weight ranking and names concrete blockers for
unsupported claim families.

## Boundary

The report generator and validator are deterministic local artifact checks.
They do not run Ollama, local OpenAI-compatible servers, hosted providers,
Hermes, OpenClaw, CLI agents, browser/email tools, shell or file actions as a
system under test, networks, private logs, credentials, gated LLM review, or
external actions.
