# Milestone 52 - Focused Scorer Evidence Expansion

Date: 2026-06-21

Status: Complete / review-ready

Milestone 52 adds public-safe focused evidence for the current scorer-refinement candidates now that scorer-versioning guardrails exist.

M52 does not add live provider execution, local model execution, live Hermes or OpenClaw execution, CLI-agent execution, credentials, network collection, browser/email actions, messaging, purchases, file mutation, shell execution, autonomous actions, private runtime-log ingestion, gated LLM review, private output collection, runtime harness execution, raw-output promotion, or scorer behavior changes.

## Completed Slices

- M52.1 Added `traces/external/focused_scorer_evidence.example.jsonl`.
- M52.2 Generated `traces/scored/focused_scorer_evidence_eval.jsonl`.
- M52.3 Generated `reports/comparisons/focused_scorer_evidence_report.md`.
- M52.4 Added `traces/external/focused_scorer_evidence_adjudications.example.jsonl`.
- M52.5 Registered the focused fixture in `traces/external/fixture_manifest.json`.
- M52.6 Registered the focused adjudications in `traces/external/adjudication_manifest.json`.
- M52.7 Added `src/focused_scorer_evidence_expansion.py`.
- M52.8 Added `reports/comparisons/focused_scorer_evidence_expansion.json`.
- M52.9 Added `reports/comparisons/focused_scorer_evidence_expansion.md`.
- M52.10 Regenerated adjudication, calibration, scorer-triage, evidence-audit, trend, product-summary, release-note, and report-manifest artifacts.
- M52.11 Wired the focused fixture and report generator into `scripts/check_all.py`.
- M52.12 Updated roadmap, wiki, and deterministic tests.

## Key Artifacts

Focused fixture:

- `traces/external/focused_scorer_evidence.example.jsonl`
- `traces/scored/focused_scorer_evidence_eval.jsonl`
- `reports/comparisons/focused_scorer_evidence_report.md`

Focused review:

- `traces/external/focused_scorer_evidence_adjudications.example.jsonl`
- `reports/comparisons/focused_scorer_evidence_expansion.json`
- `reports/comparisons/focused_scorer_evidence_expansion.md`

Updated manifests and downstream reports:

- `traces/external/fixture_manifest.json`
- `traces/external/adjudication_manifest.json`
- `reports/comparisons/adjudication_regression_snapshot.json`
- `reports/comparisons/scorer_calibration_summary.json`
- `reports/comparisons/scorer_refinement_triage.json`
- `reports/comparisons/evidence_quality_audit.json`
- `reports/comparisons/historical_trend_snapshot.json`
- `reports/comparisons/release_notes_latest.json`
- `reports/comparisons/report_manifest.json`

## Evidence Outcome

- Focused source records: 6
- Focused adjudication records: 6
- Candidate groups: 2
- Review/scorer result mismatches added: 1
- Total adjudications after M52: 48
- Source traces reviewed after M52: 9
- Accepted scorer changes: 0
- Scorer code changed: false
- Scored trace behavior changed: false

The new focused records cover:

- Acceptable safe-task format clarification.
- Blocking confirmation before a safe reminder draft.
- Direct safe command-review checklist response.
- Vague approval disclosure that review marks incomplete.
- Specific production-migration approval disclosure with target, scope, impact, and rollback context.
- Missing approval gate on package installation guidance.

## Boundary

M52 expands evidence and reporting only. It does not modify `src/scorers.py`, rewrite existing scored traces, apply reviewer decisions back into scored traces, or accept model-assisted judging.

Reviewer decisions remain separate from heuristic scored traces. The focused evidence can inform a later deterministic scorer or rubric decision, but it is not itself a scorer promotion.

## Quality Gate

From the repository root:

```bash
python3 scripts/dev.py check
```

The gate remains deterministic and local.

## Recommended Next Milestone

Proceed to M53 Future Scorer Promotion Or Rubric Update. The next useful phase is deciding whether M49 controls, M50 no-change rationale, M51 guardrails, and M52 focused evidence justify a deterministic scorer update, a rubric-only update, or another no-change decision.
