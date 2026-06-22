# Real Model Proof Path

The real-model proof path is the controlled route from evaluator-health
fixtures to a publishable local/open-weight benchmark. It is CLI/report first
and keeps live execution outside the deterministic quality gate.

## Current Status

The lab has not yet committed a real publishable model benchmark. The M70-M76
package adds the contracts needed to run one safely:

- review-summary schema and inter-rater report,
- reviewed live-local ledger checks,
- real metric aggregation in the local/open-weight report,
- hosted-provider metadata boundaries,
- operator runbook with next commands and blocked publication reason.

## Local Proof Target

The first proof target is reviewed extended `local_public_v1` evidence for two
installed Ollama models:

- `gemma4:latest`
- `llama3.2:latest`

`qwen3.5:2b-q4_K_M` is smoke/control only. `gemma4:31b-cloud` is excluded from
local/open-weight claims.

## M77 Technical Proof Profile

M77 is the first live-local proof attempt. Its target is a laptop-safe
technical pass in less than five hours, not a publishable ranked benchmark.

The M77 proof is allowed to demonstrate that the lab can:

- run real installed Ollama models with explicit live-local opt-in,
- collect raw local outputs under ignored local paths,
- score reviewed or review-pending normalized outputs,
- hash outputs, scored traces, review summaries, and ledgers,
- regenerate blocked benchmark reports that state why publication is not yet
  unlocked.

The M77 operator profile is conservative by design:

- run one model at a time,
- start with the `qwen3.5:2b-q4_K_M` smoke/control target,
- run `llama3.2:latest` before the heavier `gemma4:latest`,
- keep the laptop plugged in on a hard surface with clear airflow,
- stop or defer the heavier run if macOS memory pressure or thermal throttling
  becomes unstable.

M77 can prove the live path works. It must not claim a publishable ranking until
the full review, ledger, and two-model publication gates below are satisfied.

## Publication Gate

The local/open-weight benchmark report publishes rankings only when at least
two eligible reviewed live-local ledgers exist. Eligible entries must be:

- `evidence_class: local_public_benchmark`,
- `run_mode: reviewed_live_local_run`,
- standard or extended split,
- complete for the selected split,
- public-safe,
- free of raw outputs, private data, credentials, external actions, unresolved
  review, unsafe output flags, malformed output flags, and cloud-labelled local
  targets.

## Hosted Path

Hosted provider evidence starts as separate metadata under
`schemas/hosted_provider_batch.schema.json`. The first planned target is OpenAI
Batch for `/v1/responses`, but no hosted request/result payload, API key,
provider call, cost record, or hosted ranking claim is committed by the current
quality gate.

## Artifacts

- `reports/comparisons/live_local_review_summary.json`
- `reports/comparisons/local_open_weight_benchmark_v1.json`
- `reports/comparisons/real_model_proof_runbook.json`
- `reports/comparisons/hosted_provider_batch_summary.json`
- `docs/milestones/m70-m76-real-model-proof-roadmap-closeout.md`
