# Milestone 70-M76 - Real Model Proof Roadmap

Status: Complete / public-safe real-model proof path ready for manual opt-in runs
Date: 2026-06-22

## Summary

M70-M76 adds the public-safe contracts and product surface needed to move from
dry-run evaluator health toward a controlled, opt-in real local model proof.
The implementation does not run local models or hosted providers in the
deterministic quality gate. It prepares the review, ledger, report, hosted
metadata, and operator-runbook boundaries required before a real benchmark can
be published.

## Completed

- M70 adds `schemas/live_local_review_summary.schema.json`,
  `traces/external/live_local_review_summary.example.json`,
  `src/live_local_review_summary.py`, and aggregate reports for reviewer
  protocol, deterministic sampling, inter-rater checks, and unresolved-review
  blockers.
- M71-M73 extend local ledger validation so reviewed live-local evidence must
  pin a review summary, match reviewed record IDs, match scored trace pass
  results and severity, and reject ranking-eligible entries with unresolved,
  unsafe, malformed, private, raw-output, partial, smoke-only, or cloud-labelled
  evidence.
- M74 upgrades `src/local_benchmark_report.py` from placeholder ranking rows to
  real aggregation over reviewed scored traces: severity-weighted effective
  pass rate, heuristic pass rate, deterministic bootstrap interval, sample
  size, review counts, unresolved review count, abstention count, exclusions,
  and ledger entry ID.
- M75 adds `schemas/hosted_provider_batch.schema.json`,
  `traces/external/hosted_provider_batch_metadata.example.json`, and
  `src/hosted_provider_batch.py` for a future OpenAI Batch `/v1/responses`
  path as a separate metadata-only hosted evidence class.
- M76 adds `schemas/real_model_proof_runbook.schema.json`,
  `traces/external/real_model_proof_runbook.example.json`, and
  `src/real_model_proof_runbook.py` for the CLI/report operator product layer:
  next command, evidence status, blocked publication reason, review queue, and
  eligible/ineligible model list.

## Proof Boundary

The lab has not yet produced a real publishable model benchmark. It has now
proved the public-safe path and gates needed to run one: at least two reviewed
extended `local_public_v1` ledgers are required before the local/open-weight
benchmark report can publish a ranking.

The target manual proof path remains:

- `gemma4:latest` extended split.
- `llama3.2:latest` extended split.
- `qwen3.5:2b-q4_K_M` smoke/control only.
- `gemma4:31b-cloud` excluded from local/open-weight claims.

## Safety Boundary

The committed artifacts use fake public-safe metadata only. They do not commit
private evidence, raw local outputs, private audit reports, private paths,
credentials, secrets, raw private logs, real customer data, live provider/model
runtime execution, browser/email/network/shell/external actions, or gated LLM
review. The reports do not make public leaderboard, production-safety,
third-party reproducibility, cloud benchmark, or private-audit overclaims.

## Artifacts

- `schemas/live_local_review_summary.schema.json`
- `schemas/hosted_provider_batch.schema.json`
- `schemas/real_model_proof_runbook.schema.json`
- `traces/external/live_local_review_summary.example.json`
- `traces/external/hosted_provider_batch_metadata.example.json`
- `traces/external/real_model_proof_runbook.example.json`
- `reports/comparisons/live_local_review_summary.json`
- `reports/comparisons/live_local_review_summary.md`
- `reports/comparisons/hosted_provider_batch_summary.json`
- `reports/comparisons/hosted_provider_batch_summary.md`
- `reports/comparisons/real_model_proof_runbook.json`
- `reports/comparisons/real_model_proof_runbook.md`
- `src/live_local_review_summary.py`
- `src/hosted_provider_batch.py`
- `src/real_model_proof_runbook.py`
- `tests/test_live_local_review_summary.py`
- `tests/test_hosted_provider_batch.py`
- `tests/test_real_model_proof_runbook.py`

## Validation

- Focused tests cover review-summary validation, duplicate review records,
  unresolved review counts, reviewer aliases, inter-rater counts, ledger review
  summary matching, benchmark aggregation, fake two-ledger unlock behavior,
  hosted-provider metadata boundaries, and operator runbook publication gates.
- Full validation is `python3 scripts/dev.py check`.
