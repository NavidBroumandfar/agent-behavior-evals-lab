# Milestone 54 - Local Benchmark Claim Charter

Date: 2026-06-21

Status: Complete / review-ready

Milestone 54 turns the new evidence-first roadmap into a guarded local-first benchmark contract. It defines which claims are supported by evaluator-health artifacts, local/open-weight model evidence, manual public samples, cloud benchmark evidence, private audit evidence, promoted public evidence, and unsupported evidence.

M54 does not add live provider execution, local model execution, live Ollama calls, live Hermes or OpenClaw execution, CLI-agent execution, credentials, network collection, browser/email actions, messaging, purchases, file mutation, shell execution, autonomous actions, private runtime-log ingestion, gated LLM review, private output collection, runtime harness execution, raw-output promotion, scorer behavior changes, or scored trace rewrites.

## Completed Slices

- M54.1 Added `schemas/benchmark_claim_charter.schema.json`.
- M54.2 Added `benchmarks/evidence_class_charter.json`.
- M54.3 Added `src/validate_benchmark_claim_charter.py`.
- M54.4 Added deterministic validation tests for evidence-class and claim-boundary rules.
- M54.5 Wired benchmark claim charter validation and compile coverage into `scripts/check_all.py`.
- M54.6 Updated the schema validation coverage matrix.
- M54.7 Updated the zero-cost local-first roadmap sequence.
- M54.8 Updated wiki and release-note rollups.

## Key Artifacts

Claim charter:

- `benchmarks/evidence_class_charter.json`
- `schemas/benchmark_claim_charter.schema.json`
- `src/validate_benchmark_claim_charter.py`

Documentation:

- `docs/wiki/concepts/benchmark_claim_charter.md`
- `docs/wiki/reference/schema_validation_coverage.md`
- `docs/live_benchmark_roadmap.md`
- `docs/roadmap.md`

## Decision Outcome

- Evidence classes: 7
- Public ranking eligible classes: `cloud_public_benchmark`, `local_public_benchmark`
- Private-data-allowed classes: `private_audit`
- Credentials-required-allowed classes: `cloud_public_benchmark`, `private_audit`
- Manual public samples excluded from rankings by default: true
- Local rankings must be labeled local: true
- Cloud rankings require cloud evidence: true

The charter makes the immediate practical path explicit: first prove the lab on public-safe local/open-weight model evidence, then add manual public samples, then a disposable no-tool or mocked-tool local agent harness, then OpenClaw in a disposable sandbox, and only later private Hermes or memory-capable evidence after vault, redaction, retention, and promotion controls exist.

## Boundary

M54 is a claim-governance and validation phase. It does not run a benchmark, rank a model, call Ollama, call hosted providers, collect private evidence, or promote private evidence.

The value is that future local and cloud benchmark reports now have a machine-checked contract for what they are allowed to claim. Unsupported claims must be downgraded or refused instead of being implied by report language.

## Quality Gate

From the repository root:

```bash
python3 scripts/dev.py check
```

The gate remains deterministic, local, credential-free, and public-safe.

## Recommended Next Milestone

Proceed to M55 Public Local Benchmark Case Corpus V1. The next useful phase is building the public-safe case corpus that local Ollama or local OpenAI-compatible model runs will use.
