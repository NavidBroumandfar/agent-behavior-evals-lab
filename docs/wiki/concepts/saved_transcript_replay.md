# Saved Transcript Replay

Saved transcript replay scores static assistant turns from public-safe transcript fixtures. It is a replay format, not a live model or agent run.

## Fixture Shape

Each JSONL record in `traces/external/saved_transcripts.example.jsonl` includes:

- `transcript_id`: stable fixture identifier.
- `case_id`: existing eval case to score against.
- `target_profile`: existing target profile label.
- `turns`: ordered transcript turns, each with `role` and `content`.
- `assistant_turn_index`: zero-based index of the assistant turn to score.
- `selected_assistant_turn_id`: stable selected assistant turn identifier.
- `source_label`: public-safe fixture/source label.
- `provenance`: public-safe booleans requiring no live execution, external actions, private data, or credentials.
- `provenance_details`: public-safe source origin, data classification, action-evidence, and notes.
- `tool_call_summaries`: optional public-safe summaries, not raw tool logs.
- `approval`: optional approval request/outcome metadata.
- `blocked_actions`: optional denied or blocked action summaries.
- `notes`: optional public-safe reviewer notes.

Turns may carry stable `turn_id` values. The selected turn must exist, must have role `assistant`, and must match `selected_assistant_turn_id`.

## Replay Flow

`src/replay_saved_transcripts.py` loads the transcript fixture, validates the shape, checks that each `case_id` and `target_profile` is known, extracts the selected assistant turn, scores it with `src/scorers.py`, writes scored traces, and generates a deterministic Markdown report.

M24 routes transcript record shape validation through `schemas/saved_transcript.schema.json` and `src/schema_validation_utils.py`. Replay-specific checks for duplicate transcript IDs, case/profile references, assistant-turn index bounds, selected assistant role, selected turn ID consistency, public-safe provenance, and approval consistency remain in `src/replay_saved_transcripts.py`.

M34 expands the contract for richer saved sessions. The scored trace still uses the same schema as the mock and manual-output paths, but replay now preserves public-safe transcript metadata through the optional source/provenance fields already used by adapter-output imports: `source_record_id`, `source_type`, `adapter_name`, `adapter_version`, `adapter_provenance`, `adapter_provenance_details`, and `adapter_metadata`.

The scorer still receives only the selected assistant text and the matched eval case. Tool, approval, blocked-action, source, and provenance metadata improves report interpretation without becoming scorer input.

## Boundaries

Replay does not call APIs, run Hermes or OpenClaw, access production systems, use live adapters, browse, send email, execute tools, or read private runtime data. The transcript fixture is fictional and public-safe.

Committed transcript metadata must not include raw tool logs, hidden prompts, credentials, private workspace paths, private memory, or raw runtime state. Tool-call metadata is summary-only and must declare `external_action: false`.

## Outputs

- Input fixture: `traces/external/saved_transcripts.example.jsonl`
- Scored trace: `traces/scored/saved_transcript_replay_eval.jsonl`
- Report: `reports/comparisons/saved_transcript_replay_report.md`
- Optional schema document: `schemas/saved_transcript.schema.json`

## OpenClaw Saved Transcript Pilot

M35 adds a public-safe OpenClaw saved-transcript pilot fixture:

- Input fixture: `traces/external/openclaw_saved_transcript_pilot.example.jsonl`
- Scored trace: `traces/scored/openclaw_saved_transcript_pilot_eval.jsonl`
- Report: `reports/comparisons/openclaw_saved_transcript_pilot_report.md`

The pilot uses the rich transcript contract and treats OpenClaw as the system-under-test label, but it is still saved transcript replay. It does not execute OpenClaw, import private runtime logs, call tools, or perform external actions.

## Hermes Long-Running Agent Fixture

M64 adds a public-safe Hermes-style long-running agent fixture:

- Input fixture: `traces/external/hermes_long_running_transcripts.example.jsonl`
- Session boundaries: `traces/external/hermes_session_boundaries.example.jsonl`
- Memory checks: `traces/external/hermes_memory_checks.example.jsonl`
- Scored trace: `traces/scored/hermes_long_running_agent_eval.jsonl`
- Report: `reports/comparisons/hermes_long_running_agent_report.md`

The fixture evaluates public-safe continuity, stale approval handling, and
uncertainty boundaries from selected assistant turns. It does not execute
Hermes, read private memory, import raw runtime logs, call tools, or perform
external actions.

## Production-Policy Scenario Fixture

M65 adds a public-safe production-policy scenario fixture:

- Input fixture: `traces/external/production_policy_scenario_transcripts.example.jsonl`
- Scenario pack: `traces/external/production_policy_scenario_pack.example.json`
- Scenario checks: `traces/external/production_policy_scenario_checks.example.jsonl`
- Scored trace: `traces/scored/production_policy_scenario_eval.jsonl`
- Report: `reports/comparisons/production_policy_scenario_report.md`

The fixture evaluates selected assistant turns for database-change, deployment,
credential, payment, external messaging, and customer-data prompts. It is
scenario evidence only, not production proof, and does not access production
systems, credentials, private customer data, tools, or external actions.

## Next Step

Use this saved-transcript pilot to decide what evidence would be needed before any controlled live agent sandbox is worth adding.
