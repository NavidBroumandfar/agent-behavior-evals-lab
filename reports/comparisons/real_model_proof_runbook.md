# Real Model Proof Runbook

This M76 runbook shows the next manual CLI path to a controlled, opt-in local/open-weight proof point. It does not execute live models.

## Current Status

| Field | Value |
| --- | --- |
| Runtime | `ollama` |
| Target split | `extended` |
| Cases per primary model | 210 |
| Eligible reviewed ledgers | 1 / 2 |
| Review queue | 0 waiting, 0 unresolved |
| Local ranking claim allowed | `false` |

## M80 Second Target Decision

- Decision: replace_gemma4_for_publication_path
- Selected target: `mistral:latest` via `ollama_text_only` over `extended`.
- Replaced/deferred target: `gemma4:latest`.
- Rationale: M77 stopped the heavier gemma4 pass on swap activity. M80 keeps the two-ledger publication path moving by selecting a smaller local Ollama text-only target for M81 while deferring gemma4 until resource-stability metadata exists.
- Claim language: The local/open-weight report remains blocked until reviewed extended ledgers exist for llama3.2:latest and mistral:latest; gemma4:latest is deferred and ranking-ineligible for the current publication path.
- Decision required live execution: `false`

Pre-execution requirements:

- Run only plan-only metadata checks during M80; do not execute a local model in this decision phase.
- Before M81 live execution, confirm the selected model is locally available and use the standard ignored raw-output paths.
- Execute M81 only with AGENT_EVALS_ENABLE_LIVE_LOCAL=1 and --live-local.
- Do not use qwen3.5:2b-q4_K_M smoke/control evidence for publication.
- Keep raw outputs ignored, then review, score, and ledger only public-safe derivatives in M82.

## Next Commands

### Plan mistral extended run

`python3 scripts/live_local.py --model mistral:latest --adapter ollama_text_only --split extended --plan-only`

- Execution: `non-live`
- Raw outputs committed: `false`
- Notes: M80 plan-only command is safe for operator review and does not call the local model.

### Execute mistral extended run

`AGENT_EVALS_ENABLE_LIVE_LOCAL=1 python3 scripts/live_local.py --model mistral:latest --adapter ollama_text_only --split extended --live-local --max-failures 210`

- Execution: `live`
- Raw outputs committed: `false`
- Notes: M81 manual opt-in only; stop and keep publication blocked if model availability, memory pressure, or thermal behavior becomes unstable.

### Validate llama3.2 reviewed candidate

`python3 src/validate_adapter_outputs.py --allow-live-local traces/external/m77_llama3_2_latest_extended.reviewed.jsonl`

- Execution: `non-live`
- Raw outputs committed: `false`
- Notes: M78 produced this local ignored candidate; validation uses explicit live-local opt-in and remains outside the deterministic gate.

### Score llama3.2 reviewed candidate

`python3 src/import_adapter_outputs.py traces/external/m77_llama3_2_latest_extended.reviewed.jsonl traces/scored/m77_llama3_2_latest_extended.local.jsonl --allow-live-local --case-path evals/benchmarks/local_public_v1/cases.jsonl`

- Execution: `non-live`
- Raw outputs committed: `false`
- Notes: M79 scored the reviewed saved outputs locally without committing raw outputs or adding live-local execution to the quality gate.

### Build llama3.2 reviewed ledger

`python3 src/m79_llama3_2_reviewed_ledger.py && python3 src/validate_local_run_ledger.py traces/external/m79_llama3_2_latest_extended.local_run_ledger.json`

- Execution: `non-live`
- Raw outputs committed: `false`
- Notes: M79 built the first eligible reviewed live-local ledger for llama3.2:latest from committed public-safe derivatives.

### Validate ledgers and regenerate report

`python3 src/validate_local_run_ledger.py traces/external/m79_llama3_2_latest_extended.local_run_ledger.json && python3 src/local_benchmark_report.py`

- Execution: `non-live`
- Raw outputs committed: `false`
- Notes: Publication remains blocked because only one eligible reviewed extended ledger exists.

## Publication Gate

- Blocked reason: M79 produced one eligible reviewed live-local llama3.2 ledger, but the required M80-selected mistral second-target ledger does not exist yet.
- Complete the M80-selected mistral:latest extended target through M81 live-local execution and M82 review, scoring, and ledgering.
- Review, normalize, score, and ledger the second target with no unresolved review, unsafe output, malformed output, private data, or raw outputs.
- Regenerate the local/open-weight benchmark report after at least two eligible reviewed ledgers exist.

## Boundaries

- This runbook is CLI/report product surface only.
- Manual live-local commands require explicit operator opt-in.
- Raw outputs remain local and ignored until reviewed normalization approves public-safe evidence.
- The hosted provider path is deferred and separated from local/open-weight rankings.
- No public leaderboard, production-safety proof, third-party reproducibility claim, or private-audit overclaim is made.
