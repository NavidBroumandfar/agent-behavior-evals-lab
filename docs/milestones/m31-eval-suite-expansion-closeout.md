# Milestone 31 - Eval Suite Expansion

Date: 2026-06-20

Status: Complete / review-ready

Milestone 31 expands the deterministic mock evaluation suite from 30 to 42 cases while preserving the evaluator boundary and local quality gate.

M31 does not add live provider calls, local model execution, CLI agent execution, credentials, network collection, browser/email actions, autonomous actions, or real adapter execution inside the deterministic quality gate.

## Completed Slices

- M31.1 Added two safe direct-response cases covering shell-command review and file-permission explanation without execution.
- M31.2 Added four approval-gated cases covering production migrations, credential rotation, invoice email/payment instructions, and production release deployment.
- M31.3 Added three refusal-required cases covering credential exfiltration, audit-log evasion before payroll tampering, and deceptive monitoring installation.
- M31.4 Added three uncertainty-handling cases covering missing logs, missing prior approval context, and missing production shell-command context.
- M31.5 Regenerated the deterministic mock baseline trace and baseline/profile/failure reports.
- M31.6 Updated baseline regression snapshots and expected trace counts.
- M31.7 Expanded public-safe adjudication coverage so existing review-coverage thresholds remain meaningful after the larger baseline.
- M31.8 Regenerated adjudication-aware reports, adjudication regression snapshot, and baseline self-comparison report.

## Key Artifacts

Eval cases:

- `evals/cases/safe_task_cases.jsonl`
- `evals/cases/approval_gate_cases.jsonl`
- `evals/cases/refusal_cases.jsonl`
- `evals/cases/uncertainty_cases.jsonl`

Generated traces and reports:

- `traces/scored/baseline_mock_run.jsonl`
- `reports/baseline_report.md`
- `reports/comparisons/profile_comparison_report.md`
- `reports/comparisons/failure_inspection.md`
- `reports/comparisons/baseline_regression_snapshot.json`
- `reports/comparisons/baseline_self_comparison_report.md`
- `reports/comparisons/adjudication_summary_report.md`
- `reports/comparisons/adjudicated_aggregate_report.md`
- `reports/comparisons/adjudication_regression_snapshot.json`

Adjudication fixtures:

- `traces/external/adjudications.example.jsonl`
- `traces/external/adjudications.followup.example.jsonl`
- `traces/external/adjudication_manifest.json`

Quality gate and tests:

- `scripts/check_all.py`
- `tests/test_validate_schemas.py`

## Current Deterministic Baseline

- Eval cases: 42
- Quality-gate profiles: 3
- Baseline scored records: 126
- Passed: 115
- Failed: 11
- Failure modes: `missing_approval_gate=7`, `over_refusal=4`

Profile summary:

- `generic_assistant`: 35 passed, 7 failed
- `openclaw_reference_agent`: 42 passed, 0 failed
- `strict_approval_agent`: 38 passed, 4 failed

Category summary:

- `safe_direct_response`: 32 passed, 4 failed
- `approval_gated`: 35 passed, 7 failed
- `refusal_required`: 24 passed, 0 failed
- `uncertainty_handling`: 24 passed, 0 failed

## Adjudication Coverage

M31 adds five public-safe adjudication records over the expanded baseline. The manifest-backed adjudication snapshot now records:

- Adjudication records: 12
- Source trace records: 126
- Source trace review coverage: 9.5%
- Generic assistant review coverage: 16.7%
- Strict approval agent review coverage: 11.9%
- Approval-gated category review coverage: 11.9%
- Safe direct-response category review coverage: 13.9%
- Uncertainty-handling category review coverage: 8.3%

The existing `needs_discussion` count remains 3, so M31 expands coverage without loosening the manifest quality-gate thresholds.

## What Remains Intentionally Blocked

- Scoring changes.
- Live model or agent evaluation.
- Hermes or OpenClaw execution.
- Provider SDKs, credentials, or network collection.
- Browser, email, messaging, purchase, or file-mutation actions.
- Treating the deterministic mock baseline as production model evidence.

## Quality Gate

From the repository root:

```bash
python3 scripts/dev.py check
```

The gate validates 42 eval cases and 126 baseline scored trace records.

## Recommended Next Milestone

Milestone 32 should harden scorer and review guidance. The next practical slice is documenting known v0 scorer false positives and false negatives, then adding targeted scorer tests for the new agent-risk case families.
