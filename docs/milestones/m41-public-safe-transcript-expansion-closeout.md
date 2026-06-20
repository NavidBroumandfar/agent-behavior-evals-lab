# Milestone 41 - Public-Safe Transcript Expansion

Date: 2026-06-20

Status: Complete / review-ready

Milestone 41 expands saved transcript coverage with a new synthetic public-safe fixture family.

M41 does not add live provider execution, local model execution, live Hermes or OpenClaw execution, CLI-agent execution, credentials, network collection, browser/email actions, messaging, purchases, file mutation, shell execution, autonomous actions, private runtime-log ingestion, scorer changes, gated LLM review, or private output collection.

## Completed Slices

- M41.1 Added `traces/external/public_safe_transcript_expansion.example.jsonl` with 8 synthetic public-safe saved transcripts.
- M41.2 Generated `traces/scored/public_safe_transcript_expansion_eval.jsonl`.
- M41.3 Generated `reports/comparisons/public_safe_transcript_expansion_report.md`.
- M41.4 Added the fixture family to `traces/external/fixture_manifest.json`.
- M41.5 Wired the replay command and trace/report verification into `scripts/check_all.py`.
- M41.6 Indexed the new report in `reports/comparisons/report_manifest.json`.
- M41.7 Updated reporting product summary, evidence audit, external fixture comparison, release notes, tests, roadmap, and wiki references.

## Key Artifacts

Fixtures and generated outputs:

- `traces/external/public_safe_transcript_expansion.example.jsonl`
- `traces/scored/public_safe_transcript_expansion_eval.jsonl`
- `reports/comparisons/public_safe_transcript_expansion_report.md`

Manifest and quality gate:

- `traces/external/fixture_manifest.json`
- `reports/comparisons/report_manifest.json`
- `scripts/check_all.py`

Docs:

- `docs/wiki/concepts/public_safe_transcript_expansion.md`
- `docs/roadmap.md`
- `docs/wiki/index.md`

## Coverage Added

The M41 fixture contains 8 selected assistant turns:

- 2 safe direct-response transcripts.
- 2 approval-gated transcripts.
- 2 refusal-required transcripts.
- 2 uncertainty-handling transcripts.

The generated scored trace currently has:

- Passed: 4
- Failed: 4
- Tool-call summaries: 3
- Approval metadata records: 8
- Blocked-action summaries: 5

The fixture includes both passing and intentionally failing examples so transcript replay continues to exercise approval boundaries, refusal boundaries, safe task-following, fake completion claims, and missing-context handling.

## Promotion Notes

No private run, raw runtime log, private account session, browser/email action, shell action, file mutation, provider run, Hermes run, or OpenClaw run was promoted.

The fixture is manually authored synthetic data with public-safe metadata only.

## Boundary

The new records are not live runtime evidence and do not establish benchmark rates. They improve deterministic local fixture coverage and give M42 a broader source set to consider for future adjudication and scorer-calibration work.

## Quality Gate

From the repository root:

```bash
python3 scripts/dev.py check
```

The gate remains deterministic and local.

## Recommended Next Milestone

Proceed to M42 Scorer Calibration From Adjudications. The next useful step is to compare heuristic outcomes against committed adjudication decisions and identify which external fixture traces should be reviewed first.
