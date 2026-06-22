# Real Model Proof Path

The real-model proof path is the controlled route from evaluator-health
fixtures to a publishable local/open-weight benchmark. It is CLI/report first
and keeps live execution outside the deterministic quality gate.

## Current Status

The lab has committed its first scoped local/open-weight ranking. The M70-M76
package added the contracts needed to run one safely:

- review-summary schema and inter-rater report,
- reviewed live-local ledger checks,
- real metric aggregation in the local/open-weight report,
- hosted-provider metadata boundaries,
- operator runbook with current publication-gate state.

M77 executed the first live-local technical proof attempt. The run completed the
extended split for `llama3.2:latest` with 210 / 210 successful generations.
M78 reviewed all 210 records, approved them as public-safe text-only evidence,
and wrote an ignored reviewed normalized candidate. M79 scored a public-safe
derivative of that candidate and built the first eligible reviewed live-local
ledger for `llama3.2:latest`. `gemma4:latest` was deferred after swap activity
appeared during the heavier pass. M80 replaced `gemma4:latest` with
`mistral:latest` for the current two-ledger publication path. M81 executed the
`mistral:latest` extended run, M82 reviewed and ledgered it, and M83 published
the scoped local/open-weight ranking from two eligible reviewed ledgers.
M84 adds the public-safe reproducibility packet for that ranking. M85 records
runtime stability metadata and keeps `gemma4:latest` deferred until a future
explicit retry decision.

## Local Proof Target

The current proof target is reviewed extended `local_public_v1` evidence for
two local Ollama models:

- `llama3.2:latest`
- `mistral:latest`

`qwen3.5:2b-q4_K_M` is smoke/control only. `gemma4:latest` is deferred after
the M77 swapout blocker, and `gemma4:31b-cloud` is excluded from
local/open-weight claims.

## M77 Technical Proof Profile

M77 is the first live-local proof attempt. Its target is a laptop-safe
technical pass in less than five hours, not a publishable ranked benchmark.

The M77 proof is allowed to demonstrate that the lab can:

- run real installed Ollama models with explicit live-local opt-in,
- collect raw local outputs under ignored local paths,
- score reviewed or review-pending normalized outputs,
- hash outputs, scored traces, review summaries, and ledgers,
- regenerate benchmark reports that state whether publication is blocked or
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

## Post-M77 Roadmap

M77 is closed as a technical proof. The remaining publication work is tracked as
follow-on milestones, not as unfinished M77 scope:

- M78 reviewed and normalized the 210 `llama3.2:latest` M77 raw records into a
  local ignored candidate.
- M79 scores that reviewed evidence and builds the first reviewed live-local
  ledger. This produced the first eligible ledger for `llama3.2:latest`.
- M80 documents the second-target decision after the `gemma4:latest` swapout
  blocker. This is complete: `mistral:latest` is the selected second target for
  the current publication path, while `gemma4:latest` is deferred.
- M81 executed the selected `mistral:latest` extended run after explicit
  live-local opt-in. The ignored local raw run completed 210 / 210 records.
- M82 reviewed, normalized, scored, and ledgered the `mistral:latest` second
  target, producing the second eligible reviewed live-local ledger.
- M83 regenerated the local/open-weight benchmark report from two eligible
  reviewed live-local ledgers and published the local ranking.
- M84 adds a public-safe reproducibility packet.
- M85 adds runtime stability and resource-profile metadata. This is complete:
  `gemma4:latest` remains deferred, and interrupted heavy-model runs remain
  operational blockers rather than ranking evidence.
- M86 adds a final claim-review and release checklist.

These milestones exist to make the proof path auditable. They keep live-local
execution, raw output storage, review, ledger construction, report generation,
and claim approval as separate gates.

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

The current report satisfies that gate for `llama3.2:latest` and
`mistral:latest`. It remains limited to local/open-weight evidence and does not
claim production safety, hosted-provider ranking, private-audit proof, or
third-party reproducibility.

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
- `reports/comparisons/m78_llama3_2_review_normalization.json`
- `reports/comparisons/m79_llama3_2_score_ledger.json`
- `reports/comparisons/local_open_weight_benchmark_v1.json`
- `traces/external/m79_llama3_2_latest_extended.local_run_ledger.json`
- `traces/external/m82_mistral_latest_extended.local_run_ledger.json`
- `docs/milestones/m80-second-local-target-safety-decision-closeout.md`
- `docs/milestones/m70-m76-real-model-proof-roadmap-closeout.md`
- `docs/milestones/m77-controlled-live-local-technical-proof-run-closeout.md`
- `docs/milestones/m78-review-normalize-llama3-2-evidence-closeout.md`
- `docs/milestones/m79-score-ledger-llama3-2-live-local-closeout.md`
- `docs/milestones/m81-second-local-target-live-run-closeout.md`
- `docs/milestones/m82-review-score-ledger-mistral-closeout.md`
- `docs/milestones/m83-two-model-report-unlock-closeout.md`
- `docs/milestones/m84-public-safe-reproducibility-packet-closeout.md`
- `docs/milestones/m85-runtime-stability-resource-profile-closeout.md`
- `docs/wiki/concepts/public_safe_reproducibility_packet.md`
- `docs/wiki/concepts/runtime_stability_resource_profile.md`
