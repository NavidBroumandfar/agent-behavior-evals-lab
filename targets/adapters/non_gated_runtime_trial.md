# Optional Non-Gated Runtime Trial Procedure

M44 defines a manual runtime-trial procedure without adding runtime execution to the deterministic quality gate.

The current closeout decision is to defer live execution. This procedure remains available for a future manually approved trial only if saved outputs, saved transcripts, and normalized adapter outputs stop preserving the evidence needed for evaluation.

## Prepared Prompt

Use exactly one committed public-safe eval case:

- Case ID: `APPROVAL-014`
- Source: `evals/cases/approval_gate_cases.jsonl`
- Target profile: `openclaw_reference_agent`

Do not add private prompts, private memory, account context, private workspace paths, credentials, or runtime logs.

## Manual Controls

A future trial must be:

- Manual and non-gated.
- Disposable.
- Text-only final assistant output.
- Tools disabled.
- Network access disabled.
- Credentials absent.
- Browser, email, messaging, purchase, deployment, shell, and file-mutation actions blocked.
- Reviewed and sanitized before any promotion.

The deterministic quality gate may validate this procedure and metadata, but it must not run the runtime, collect raw output, validate raw local output, or score local trial output.

## Local Output Policy

If a future human-approved manual trial is run, raw output must stay local-only:

- Raw output: `traces/raw/m44_non_gated_runtime_trial.local.jsonl`
- Local scored trace, if created during review: `traces/scored/m44_non_gated_runtime_trial.local.jsonl`

Raw local files are not committable.

Reviewed output may only be proposed later as:

- Reviewed output candidate: `traces/external/m44_non_gated_runtime_trial.reviewed.jsonl`
- Format: adapter-output JSONL
- Validator: `python3 src/validate_adapter_outputs.py traces/external/m44_non_gated_runtime_trial.reviewed.jsonl`
- Importer: `python3 src/import_adapter_outputs.py traces/external/m44_non_gated_runtime_trial.reviewed.jsonl`

Promotion requires separate review notes, public-safe provenance, fixture manifest updates, report regeneration, and quality-gate validation.

## Stop Conditions

Stop and discard the trial if any of these are required:

- Credentials, tokens, private accounts, or private workspace paths.
- Network collection.
- Browser, email, messaging, purchase, deployment, shell, or file-mutation actions.
- Private runtime logs or hidden prompts.
- Gated LLM review.
- Claims that the output is benchmark evidence before promotion.
