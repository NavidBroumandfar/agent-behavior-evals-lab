# Milestone 35 - OpenClaw Saved-Transcript Pilot

Date: 2026-06-20

Status: Complete / review-ready

Milestone 35 adds a public-safe OpenClaw saved-transcript pilot using the rich M34 transcript contract.

M35 does not add live OpenClaw execution, Hermes execution, provider calls, local model execution, CLI agent execution, credentials, network collection, browser/email actions, messaging, purchases, file mutation, autonomous actions, raw runtime-log ingestion, or live adapter execution inside the deterministic quality gate.

## Completed Slices

- M35.1 Extended `src/replay_saved_transcripts.py` with CLI options for input path, output path, report path, run ID, timestamp, report title, and report context.
- M35.2 Added `traces/external/openclaw_saved_transcript_pilot.example.jsonl` with three public-safe OpenClaw-style saved transcript records.
- M35.3 Generated `traces/scored/openclaw_saved_transcript_pilot_eval.jsonl`.
- M35.4 Generated `reports/comparisons/openclaw_saved_transcript_pilot_report.md`.
- M35.5 Added the pilot fixture to `traces/external/fixture_manifest.json`.
- M35.6 Added the pilot report to `reports/comparisons/report_manifest.json` and report-manifest coverage checks.
- M35.7 Wired the deterministic gate to replay the static pilot fixture without live runtime execution.
- M35.8 Regenerated `reports/comparisons/external_fixture_comparison_report.md`.
- M35.9 Added tests for custom saved-transcript replay paths and updated manifest-count expectations.
- M35.10 Updated roadmap, wiki docs, and milestone index.

## Key Artifacts

Code and tests:

- `src/replay_saved_transcripts.py`
- `scripts/check_all.py`
- `tests/test_saved_transcript_replay.py`
- `tests/test_fixture_manifest_validation.py`
- `tests/test_report_manifest_validation.py`

Pilot fixture and generated artifacts:

- `traces/external/openclaw_saved_transcript_pilot.example.jsonl`
- `traces/scored/openclaw_saved_transcript_pilot_eval.jsonl`
- `reports/comparisons/openclaw_saved_transcript_pilot_report.md`
- `reports/comparisons/external_fixture_comparison_report.md`

Manifests and docs:

- `traces/external/fixture_manifest.json`
- `reports/comparisons/report_manifest.json`
- `docs/wiki/concepts/saved_transcript_replay.md`
- `docs/roadmap.md`
- `docs/wiki/index.md`

## Pilot Scope

The pilot has three public-safe selected-turn transcript records:

- `APPROVAL-014`: production release merge/deploy approval gate.
- `REFUSAL-007`: audit-log evasion and payroll tampering refusal.
- `UNCERTAINTY-008`: missing production shell-command context.

Current pilot result:

- Saved transcript records: 3
- Passed: 3
- Failed: 0

## Boundary

OpenClaw is treated as the system-under-test label for this pilot fixture, but the quality gate only replays committed saved transcripts. It does not run OpenClaw, inspect a private OpenClaw runtime, execute tools, collect network output, or perform external actions.

The pilot report explicitly avoids benchmark or leaderboard claims. It is evidence that the evaluator can score a public-safe OpenClaw saved-transcript fixture through the same deterministic replay path.

## External Fixture Impact

The manifest-driven external fixture comparison now includes:

- Source groups: 6
- Total scored external fixture records: 26
- Failed records: 11

## What Remains Intentionally Blocked

- Live Hermes or OpenClaw runtime execution.
- Deep harness integration.
- Raw private transcript/log import.
- Credentials, private prompts, account identifiers, private memory, or private workspace paths in committed fixtures.
- Browser, email, messaging, purchase, file mutation, or other external actions.
- Treating the small sanitized pilot as production benchmark evidence.

## Quality Gate

From the repository root:

```bash
python3 scripts/dev.py check
```

The gate remains deterministic and local.

## Recommended Next Milestone

Milestone 36 should add a controlled live agent sandbox only if there is a clear need beyond saved transcript replay. Start with tools disabled or mocked, a disposable workspace, no credentials, and local-only raw outputs.
