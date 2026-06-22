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

`AGENT_EVALS_ENABLE_LIVE_LOCAL=1 python3 scripts/live_local.py --model gemma4:latest --adapter ollama_text_only --split extended --live-local`

- Execution: `live`
- Raw outputs committed: `false`
- Notes: Manual opt-in only; raw outputs must remain under ignored local paths until reviewed.

### Execute llama3.2 extended run

`AGENT_EVALS_ENABLE_LIVE_LOCAL=1 python3 scripts/live_local.py --model llama3.2:latest --adapter ollama_text_only --split extended --live-local`

- Execution: `live`
- Raw outputs committed: `false`
- Notes: Manual opt-in only; needed as the second eligible model before local rankings can publish.

### Normalize reviewed outputs

`python3 src/review_text_only_outputs.py --allow-live-local <raw-local-jsonl> <reviewed-normalized-jsonl>`

- Execution: `non-live`
- Raw outputs committed: `false`
- Notes: Only reviewed, public-safe normalized outputs may move into committed evidence paths.

### Validate ledger and regenerate report

`python3 src/validate_local_run_ledger.py <reviewed-ledger.json> && python3 src/local_benchmark_report.py`

- Execution: `non-live`
- Raw outputs committed: `false`
- Notes: Publication remains blocked until two eligible reviewed extended ledgers exist with no unresolved review.

## Publication Gate

- Blocked reason: No reviewed live-local extended ledgers exist for the two primary local targets yet.
- Run the extended split for gemma4:latest and llama3.2:latest with explicit live-local opt-in.
- Keep raw outputs local and ignored until review approves public-safe normalized outputs.
- Review every failed case, every high or critical case, and the deterministic pass sample.
- Build ledgers with local_public_benchmark evidence class and no unresolved review, unsafe output, malformed output, private data, or raw outputs.
- Regenerate the local/open-weight benchmark report after at least two eligible reviewed ledgers exist.

## Boundaries

- This runbook is CLI/report product surface only.
- Manual live-local commands require explicit operator opt-in.
- Raw outputs remain local and ignored until reviewed normalization approves public-safe evidence.
- The hosted provider path is deferred and separated from local/open-weight rankings.
- No public leaderboard, production-safety proof, third-party reproducibility claim, or private-audit overclaim is made.
