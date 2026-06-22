# Real Model Proof Runbook

This M76 runbook shows the next manual CLI path to a controlled, opt-in local/open-weight proof point. It does not execute live models.

## Current Status

| Field | Value |
| --- | --- |
| Runtime | `ollama` |
| Target split | `extended` |
| Cases per primary model | 210 |
| Eligible reviewed ledgers | 0 / 2 |
| Review queue | 0 waiting, 0 unresolved |
| Local ranking claim allowed | `false` |

## Next Commands

### Plan gemma4 extended run

`python3 scripts/live_local.py --model gemma4:latest --adapter ollama_text_only --split extended --plan-only`

- Execution: `non-live`
- Raw outputs committed: `false`
- Notes: Plan-only command is safe for operator review and does not call the local model.

### Execute gemma4 extended run

`AGENT_EVALS_ENABLE_LIVE_LOCAL=1 python3 scripts/live_local.py --model gemma4:latest --adapter ollama_text_only --split extended --live-local --max-failures 210`

- Execution: `live`
- Raw outputs committed: `false`
- Notes: Manual opt-in only; defer or replace this target if memory pressure or thermal behavior becomes unstable.

### Validate llama3.2 reviewed candidate

`python3 src/validate_adapter_outputs.py --allow-live-local traces/external/m77_llama3_2_latest_extended.reviewed.jsonl`

- Execution: `non-live`
- Raw outputs committed: `false`
- Notes: M78 produced this local ignored candidate; validation uses explicit live-local opt-in and remains outside the deterministic gate.

### Score llama3.2 reviewed candidate

`python3 src/import_adapter_outputs.py traces/external/m77_llama3_2_latest_extended.reviewed.jsonl traces/scored/m77_llama3_2_latest_extended.local.jsonl --allow-live-local --case-path evals/benchmarks/local_public_v1/cases.jsonl`

- Execution: `non-live`
- Raw outputs committed: `false`
- Notes: M79 should score the reviewed saved outputs locally without committing raw outputs or adding live-local execution to the quality gate.

### Build llama3.2 reviewed ledger

`python3 src/validate_local_run_ledger.py <llama32-reviewed-ledger.json>`

- Execution: `non-live`
- Raw outputs committed: `false`
- Notes: The first ledger can become eligible only if it references reviewed normalized output, scored trace, run metadata, and review summary with no unresolved blockers.

### Validate ledgers and regenerate report

`python3 src/validate_local_run_ledger.py <reviewed-ledger.json> && python3 src/local_benchmark_report.py`

- Execution: `non-live`
- Raw outputs committed: `false`
- Notes: Publication remains blocked until two eligible reviewed extended ledgers exist with no unresolved review.

## Publication Gate

- Blocked reason: M78 produced a local ignored reviewed normalized llama3.2 candidate, but no scored live-local trace, M58-compatible reviewed ledger, or second eligible local target ledger exists yet.
- Score the M78 llama3.2 reviewed normalized candidate with explicit --allow-live-local and the local_public_v1 case path.
- Build and validate an M58-compatible reviewed live-local ledger for llama3.2:latest.
- Complete or replace the second local extended target after the M77 gemma4:latest swapout blocker.
- Review, normalize, score, and ledger the second target with no unresolved review, unsafe output, malformed output, private data, or raw outputs.
- Regenerate the local/open-weight benchmark report after at least two eligible reviewed ledgers exist.

## Boundaries

- This runbook is CLI/report product surface only.
- Manual live-local commands require explicit operator opt-in.
- Raw outputs remain local and ignored until reviewed normalization approves public-safe evidence.
- The hosted provider path is deferred and separated from local/open-weight rankings.
- No public leaderboard, production-safety proof, third-party reproducibility claim, or private-audit overclaim is made.
