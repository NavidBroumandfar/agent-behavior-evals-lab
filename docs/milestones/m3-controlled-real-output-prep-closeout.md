# Milestone 3 — Controlled Real-Output Evaluation Preparation

Milestone 3 prepares Agent Behavior Evals Lab to score real saved outputs later without adding live adapters or changing evaluator logic. The lab remains the evaluator: target systems provide saved outputs, and the local pipeline scores, traces, reports, and validates them deterministically.

## What M3 Added

- Manual output evaluation mode for saved or pasted assistant/model outputs.
- Sanitized OpenClaw-style sample evaluation as a public-safe system-under-test example.
- Saved transcript replay format for scoring selected assistant turns from static transcripts.
- Adapter contract refinement that separates target-side output collection from evaluator-side scoring.
- Real model adapter design note for future adapter work without live implementation.

## Key Artifacts

- `src/evaluate_manual_outputs.py`
- `src/replay_saved_transcripts.py`
- `traces/external/manual_outputs.example.jsonl`
- `traces/external/openclaw_manual_samples.example.jsonl`
- `traces/external/saved_transcripts.example.jsonl`
- `traces/scored/manual_output_eval.jsonl`
- `traces/scored/openclaw_manual_eval.jsonl`
- `traces/scored/saved_transcript_replay_eval.jsonl`
- `reports/comparisons/manual_output_report.md`
- `reports/comparisons/openclaw_manual_eval_report.md`
- `reports/comparisons/saved_transcript_replay_report.md`
- `schemas/saved_transcript.schema.json`
- `docs/wiki/concepts/openclaw_as_system_under_test.md`
- `docs/wiki/concepts/saved_transcript_replay.md`
- `targets/adapters/adapter_contract.md`
- `targets/adapters/manual_output_adapter_contract.md`
- `targets/adapters/saved_transcript_adapter_contract.md`
- `targets/adapters/future_adapter_types.md`
- `targets/adapters/real_model_adapter_design.md`

## Quality Gate Status

`python3 scripts/check_all.py` passes with:

- deterministic mock baseline generation
- manual output evaluation generation
- OpenClaw-style manual sample evaluation generation
- saved transcript replay generation
- generated trace count checks
- report generation
- regression snapshot check
- unit tests, schema validation, and Python compile checks

Generated artifacts use fixed run IDs, fixed timestamps, deterministic ordering, and relative paths. The quality gate has no live network, provider, browser, email, agent runtime, or private workspace dependency.

## Boundary Confirmation

- The lab remains the evaluator.
- OpenClaw is only one possible system under test.
- No private runtime integration is present.
- No real APIs or live model calls are active.
- No browser, email, messaging, purchase, file mutation, or other external action is part of the milestone.
- No credentials, SDKs, paid-provider logic, autonomous agents, or background jobs were added.
- OpenClaw-style examples are fictional, sanitized fixtures, not live runtime evidence.

## What M3 Enables

- Score manually saved assistant/model outputs against existing eval cases.
- Score sanitized system-under-test samples without live execution.
- Replay public-safe saved transcripts and score selected assistant turns.
- Prepare future real adapters through a normalized output contract without changing scorer logic.

## Limitations

- The scorer remains heuristic and should not be treated as behavioral truth.
- Saved outputs have limited provenance unless future adapters add stronger public-safe source metadata.
- Transcript replay scores selected final assistant text only; it does not replay tool calls, approvals, or hidden state.
- Real adapters are designed but not implemented.
- OpenClaw-style samples are fictional and sanitized, not evidence from a live OpenClaw runtime.

## Recommended M4 Direction

Keep M4 conservative:

- Add normalized adapter output schema validation.
- Add a fixture importer or dry-run adapter that does not call providers.
- Strengthen report comparison across external fixtures.
- Consider a provider-agnostic adapter interface.
- Keep live provider calls outside `python3 scripts/check_all.py`.

## Tag Readiness

After the quality gate passes and the working tree is clean, this milestone is ready for:

`v0.3.0-controlled-real-output-prep`
