# Live Local Text-Only Harness

M57 adds an opt-in harness for running local text-only models against the
frozen `local_public_v1` public benchmark corpus.

Primary artifacts:

- `scripts/live_local.py`
- `src/live_local_harness.py`
- `schemas/live_local_run.schema.json`
- `src/validate_live_local_run.py`
- `traces/external/live_local_run_plan.example.json`

## Scope

The harness supports the live-local adapter classes declared by the M56 local
adapter registry:

- `ollama_text_only`
- `local_openai_compatible_text_only`

It runs public-safe user prompts only, sends a tools-disabled text-only system
message, checks local model availability, applies per-request timeouts, retries
generation failures up to the configured attempt count, and aborts after the
configured failure threshold.

## Opt-In Controls

Live local execution requires both controls:

- `--live-local`
- `AGENT_EVALS_ENABLE_LIVE_LOCAL` set to a truthy value

Without those controls, the command can only build a dry-run plan. The
deterministic quality gate validates `traces/external/live_local_run_plan.example.json`
with `src/validate_live_local_run.py`; it does not execute the live harness.

## Output Flow

Live runs write ignored local raw outputs under `traces/raw/*.local.jsonl` and
ignored run metadata under `traces/raw/*.local.json`.

Raw records start as `pending_review` and preserve live-local provenance. A
reviewer must mark successful records as `approved_public_safe` before
`src/review_text_only_outputs.py` can produce normalized adapter-output JSONL.

Reviewed live-local normalized outputs require explicit opt-in validation and
import:

```bash
python3 src/validate_adapter_outputs.py --allow-live-local traces/external/example.reviewed.jsonl
python3 src/import_adapter_outputs.py traces/external/example.reviewed.jsonl traces/scored/example.local.jsonl --allow-live-local --case-path evals/benchmarks/local_public_v1/cases.jsonl
```

## Boundary

M57 does not add provider credentials, hosted provider calls, private logs,
browser/email actions, shell or file actions as a system under test, external
actions, gated LLM review, leaderboard claims, or ranking methodology.

Failed or partial live-local runs are marked in local metadata and excluded from
ranking by default. M58 is responsible for a reproducible local run ledger.
