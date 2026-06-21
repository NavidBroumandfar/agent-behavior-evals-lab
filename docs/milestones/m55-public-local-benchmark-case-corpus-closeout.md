# Milestone 55 - Public Local Benchmark Case Corpus V1

Date: 2026-06-21

Status: Complete / review-ready

Milestone 55 adds the first frozen public-safe local benchmark case corpus. The corpus is designed for future zero-cost local/open-weight model runs, starting with Ollama or local OpenAI-compatible text-only adapters.

M55 does not add live provider execution, local model execution, live Ollama calls, live Hermes or OpenClaw execution, CLI-agent execution, credentials, network collection, browser/email actions, messaging, purchases, file mutation outside committed corpus generation, shell execution as a system under test, autonomous actions, private runtime-log ingestion, gated LLM review, private output collection, runtime harness execution, raw-output promotion, model ranking, scorer behavior changes, or scored trace rewrites.

## Completed Slices

- M55.1 Added deterministic corpus generator `src/local_benchmark_corpus.py`.
- M55.2 Added `evals/benchmarks/local_public_v1/cases.jsonl`.
- M55.3 Added `evals/benchmarks/local_public_v1/manifest.json`.
- M55.4 Added `schemas/local_benchmark_case.schema.json`.
- M55.5 Added `schemas/local_benchmark_manifest.schema.json`.
- M55.6 Added `src/validate_local_benchmark_corpus.py`.
- M55.7 Added deterministic tests for corpus generation, validation, coverage, hash, split, source-path, and safety guardrails.
- M55.8 Wired corpus generation, validation, and compile coverage into `scripts/check_all.py`.
- M55.9 Updated schema coverage, wiki, roadmap, and release-note rollups.

## Key Artifacts

Corpus:

- `evals/benchmarks/local_public_v1/cases.jsonl`
- `evals/benchmarks/local_public_v1/manifest.json`

Contracts and validation:

- `schemas/local_benchmark_case.schema.json`
- `schemas/local_benchmark_manifest.schema.json`
- `src/local_benchmark_corpus.py`
- `src/validate_local_benchmark_corpus.py`
- `tests/test_local_benchmark_corpus.py`

Documentation:

- `docs/wiki/concepts/local_public_benchmark_corpus.md`
- `docs/wiki/reference/schema_validation_coverage.md`
- `docs/live_benchmark_roadmap.md`
- `docs/roadmap.md`

## Corpus Outcome

- Case set: `local_public_v1`
- Version: `1.0.0`
- Total cases: 210
- Risk areas: 7
- Cases per risk area: 30
- Smoke split: 21 cases
- Standard split: 70 cases
- Extended split: 210 cases
- Difficulty bands: easy, medium, hard
- Case-file hash recorded in manifest: true

Coverage:

- Safe tasks
- Approval-gated actions
- Refusal-required misuse requests
- Uncertainty and missing-context handling
- Tool-use and fake-completion claim boundaries
- Privacy-boundary requests
- Production-change approval boundaries

## Boundary

M55 is a corpus phase. It creates the benchmark inputs that future local model runs will use, but it does not run models or rank them.

The existing 42-case baseline harness is unchanged. M55 keeps `local_public_v1` under `evals/benchmarks/` so future M56/M57 adapter work can consume it without rewriting historical baseline traces or changing current report counts.

## Quality Gate

From the repository root:

```bash
python3 scripts/dev.py check
```

The gate remains deterministic, local, credential-free, and public-safe.

## Recommended Next Milestone

Proceed to M56 Ollama And Local OpenAI-Compatible Adapter Registry. The next useful phase is adding opt-in adapter metadata and dry-run validation paths so local model runs can target `local_public_v1` without entering the deterministic quality gate.
