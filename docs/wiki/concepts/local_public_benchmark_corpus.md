# Local Public Benchmark Corpus

M55 adds `local_public_v1`, a frozen public-safe case corpus for future zero-cost local/open-weight model runs.

Primary artifacts:

- `evals/benchmarks/local_public_v1/cases.jsonl`
- `evals/benchmarks/local_public_v1/manifest.json`
- `schemas/local_benchmark_case.schema.json`
- `schemas/local_benchmark_manifest.schema.json`
- `src/local_benchmark_corpus.py`
- `src/validate_local_benchmark_corpus.py`

## Scope

The corpus contains 210 public-safe cases:

- 30 safe-task cases
- 30 approval-gate cases
- 30 refusal-boundary cases
- 30 uncertainty cases
- 30 tool-use-claim cases
- 30 privacy-boundary cases
- 30 production-change cases

The records include policy references, expected behavior, failure modes, severity, difficulty, and split membership. They are designed for future local Ollama or local OpenAI-compatible text-only runs, with tools disabled.

## Splits

The split policy is deterministic and frozen for `local_public_v1`:

- `smoke`: first 3 cases per risk area, 21 total
- `standard`: first 10 cases per risk area, 70 total
- `extended`: all 210 cases

The manifest includes the case-file SHA-256 hash so changes to the JSONL file are detected by validation.

## Boundary

M55 adds a case corpus only. It does not run Ollama, local models, cloud providers, Hermes, OpenClaw, CLI agents, browser/email tools, shell commands, file mutations, network collectors, private logs, credentials, gated LLM review, or external actions.

The corpus can support future local/open-weight benchmark runs after M56 and M57 add opt-in adapter and local harness support. It does not by itself rank models or prove production policy compliance.
