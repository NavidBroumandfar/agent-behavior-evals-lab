# Milestone 34 - Rich Saved Transcript Contract

Date: 2026-06-20

Status: Complete / review-ready

Milestone 34 expands saved transcript replay so public-safe saved sessions can preserve selected-turn, tool-summary, approval, blocked-action, source, and provenance metadata without changing scorer ownership.

M34 does not add live provider calls, local model execution, CLI agent execution, live OpenClaw execution, credentials, network collection, browser/email actions, messaging, purchases, file mutation, autonomous actions, or live adapter execution inside the deterministic quality gate.

## Completed Slices

- M34.1 Expanded `schemas/saved_transcript.schema.json` with required `selected_assistant_turn_id`, required `source_label`, required public-safe `provenance`, and required `provenance_details`.
- M34.2 Added optional `tool_call_summaries`, `approval`, and `blocked_actions` sections for public-safe session interpretation.
- M34.3 Updated `src/replay_saved_transcripts.py` to validate selected turn ID consistency, public-safe provenance, summarized tool-action metadata, and approval consistency.
- M34.4 Preserved transcript metadata in generated scored traces through existing optional source/provenance fields while keeping scoring based on selected assistant text only.
- M34.5 Updated the committed saved transcript fixture to use stable turn IDs, provenance metadata, approval metadata, and blocked/tool summaries where relevant.
- M34.6 Regenerated the saved transcript replay scored trace and report.
- M34.7 Added focused tests for required rich fields, raw-log rejection, selected turn ID mismatch, unsafe provenance, and approval consistency.
- M34.8 Updated saved transcript docs, roadmap, and wiki index.

## Key Artifacts

Code and schemas:

- `schemas/saved_transcript.schema.json`
- `src/replay_saved_transcripts.py`
- `tests/test_saved_transcript_replay.py`

Fixtures and generated artifacts:

- `traces/external/saved_transcripts.example.jsonl`
- `traces/scored/saved_transcript_replay_eval.jsonl`
- `reports/comparisons/saved_transcript_replay_report.md`

Docs:

- `docs/wiki/concepts/saved_transcript_replay.md`
- `docs/roadmap.md`
- `docs/wiki/index.md`

## Contract Boundary

The rich transcript contract represents saved sessions without importing private runtime state.

Committed transcript fixtures may include:

- Stable transcript IDs and selected assistant turn IDs.
- Public-safe source labels and provenance details.
- Tool-call summaries with `external_action=false`.
- Approval request and outcome metadata.
- Denied, blocked, or not-attempted action summaries.

Committed transcript fixtures must not include:

- Raw tool logs.
- Hidden prompts.
- Credentials, secrets, tokens, or account identifiers.
- Private memory, private workspace paths, or raw runtime state.
- Evidence of live external actions inside deterministic fixtures.

## Scoring Boundary

Replay still extracts only the selected assistant turn text for `src/scorers.py`. Rich transcript metadata is preserved in trace source/provenance fields and reports for interpretation, not used as scorer input.

## Current Saved Transcript Baseline

- Saved transcript records: 5
- Passed: 3
- Failed: 2
- The pass/fail counts remain unchanged from M33.

## What Remains Intentionally Blocked

- Live Hermes or OpenClaw execution.
- Provider SDKs or credentials.
- Browser, email, messaging, purchase, file mutation, or other external actions.
- Raw runtime-log ingestion.
- Treating fictional transcript fixtures as real runtime benchmark evidence.

## Quality Gate

From the repository root:

```bash
python3 scripts/dev.py check
```

The gate remains deterministic and local.

## Recommended Next Milestone

Milestone 35 should use the rich transcript contract for one public-safe Hermes or OpenClaw saved-transcript pilot, starting with whichever runtime can export the cleanest sanitized selected-turn transcript.
