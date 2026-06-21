# Agent Behavior Evals Lab Release Notes

## Summary

| Field | Value |
| --- | --- |
| Generated at | `2026-06-21T00:00:00Z` |
| Release ID | `release_notes_latest` |
| Quality gate command | `python3 scripts/dev.py check` |
| Indexed report artifacts | 37 |
| Baseline pass rate | 91.3% |
| Harness bridge decision | `defer_harness_integration` |

## Highlights

- **Reporting**: Maintains dashboard-ready JSON, product summary Markdown, release-note outputs, and report-manifest coverage from local artifacts.
- **Quality Gate**: Local deterministic gate remains stable; no live runtime integration is enabled.
- **Harness Boundary**: Harness decision remains defer_harness_integration; runtime-native state required is false.
- **Review**: 48 adjudication records are tracked; 0 still need discussion.
- **Evidence Quality**: Added a deterministic evidence inventory and gap report for fixture, scorer, adjudication, and reporting coverage.
- **Transcript Expansion**: Added synthetic public-safe saved transcripts covering task-following, approval, refusal, and uncertainty behavior.
- **Scorer Calibration**: Added advisory calibration labels for scorer false positives, false negatives, ambiguous reviews, and upheld outcomes.
- **Historical Trends**: Added versioned evaluator-health trend snapshots for pass rates, failure modes, adjudication outcomes, fixture counts, and report coverage.
- **Runtime Trial**: Added a validation-only optional runtime-trial plan with manual, disposable, non-gated controls and a reviewed-output promotion path.
- **External Fixture Review**: Added public-safe adjudication coverage for selected saved-transcript and normalized adapter-output scored traces.
- **Review Resolution**: Resolved the remaining public-safe needs_discussion adjudications while keeping reviewer decisions separate from heuristic traces.
- **Scorer Triage**: Recorded a no-change deterministic scorer decision and deferred refinement candidates until more focused evidence exists.
- **Review Expansion**: Expanded public-safe adjudication coverage across previously unreviewed external fixture trace families.
- **Scorer Controls**: Added focused deterministic controls for current scorer-refinement candidates without accepting scorer-code changes.
- **Scorer Decision**: Recorded a durable no-change scorer decision from M49 controls while preserving historical adjudication context.
- **Scorer Versioning**: Added optional historical scorer context validation so future scorer changes can preserve pre-change adjudication outcomes.
- **Focused Scorer Evidence**: Added public-safe focused evidence for safe-task clarification and approval-disclosure scorer candidates without accepting scorer-code changes.
- **Scorer Promotion**: Recorded a rubric-only approval-disclosure update while keeping deterministic scorer behavior and scored traces unchanged.
- **Benchmark Claims**: Added an evidence-class claim charter that separates local benchmark, cloud benchmark, manual sample, private audit, promoted public evidence, and unsupported claims.
- **Local Benchmark Corpus**: Added frozen local_public_v1 public-safe benchmark cases with deterministic smoke, standard, and extended splits for future local model runs.
- **Local Adapter Registry**: Added Ollama, local OpenAI-compatible, and manual saved-output adapter registry entries with live-local opt-in guardrails.
- **Live Local Harness**: Added an opt-in local text-only harness with dry-run plan validation, fake-client tests, and reviewed live-local output import guarded by explicit flags.
- **Local Run Ledger**: Added a reproducible local run ledger that pins case, prompt, adapter, output, scorer, and metadata hashes while validating public-safe fake examples only in the deterministic gate.

## Dashboard Snapshot

| Metric | Value |
| --- | ---: |
| Baseline records | 126 |
| Baseline failed | 11 |
| External fixture groups | 8 |
| External fixture records | 40 |
| Adjudication records | 48 |
| Review records needing discussion | 0 |

## Milestone Rollup

| Milestone | Status | Closeout |
| --- | --- | --- |
| `M35` | Complete / review-ready | `docs/milestones/m35-openclaw-saved-transcript-pilot-closeout.md` |
| `M36` | Complete / review-ready | `docs/milestones/m36-controlled-live-agent-sandbox-closeout.md` |
| `M37` | Complete / review-ready | `docs/milestones/m37-optional-harness-integration-decision-closeout.md` |
| `M38` | Complete / review-ready | `docs/milestones/m38-reporting-product-layer-closeout.md` |
| `M39` | Complete / review-ready | `docs/milestones/m39-release-notes-reporting-closeout.md` |
| `M40` | Complete / review-ready | `docs/milestones/m40-evidence-quality-audit-closeout.md` |
| `M41` | Complete / review-ready | `docs/milestones/m41-public-safe-transcript-expansion-closeout.md` |
| `M42` | Complete / review-ready | `docs/milestones/m42-scorer-calibration-closeout.md` |
| `M43` | Complete / review-ready | `docs/milestones/m43-historical-trend-snapshots-closeout.md` |
| `M44` | Complete / review-ready | `docs/milestones/m44-optional-non-gated-runtime-trial-closeout.md` |
| `M45` | Complete / review-ready | `docs/milestones/m45-external-fixture-adjudication-coverage-closeout.md` |
| `M46` | Complete / review-ready | `docs/milestones/m46-needs-discussion-resolution-closeout.md` |
| `M47` | Complete / review-ready | `docs/milestones/m47-deterministic-scorer-refinement-triage-closeout.md` |
| `M48` | Complete / review-ready | `docs/milestones/m48-external-fixture-review-expansion-closeout.md` |
| `M49` | Complete / review-ready | `docs/milestones/m49-scorer-candidate-control-tests-closeout.md` |
| `M50` | Complete / review-ready | `docs/milestones/m50-deterministic-scorer-change-decision-closeout.md` |
| `M51` | Complete / review-ready | `docs/milestones/m51-scorer-versioning-guardrails-closeout.md` |
| `M52` | Complete / review-ready | `docs/milestones/m52-focused-scorer-evidence-expansion-closeout.md` |
| `M53` | Complete / review-ready | `docs/milestones/m53-scorer-promotion-or-rubric-update-closeout.md` |
| `M54` | Complete / review-ready | `docs/milestones/m54-local-benchmark-claim-charter-closeout.md` |
| `M55` | Complete / review-ready | `docs/milestones/m55-public-local-benchmark-case-corpus-closeout.md` |
| `M56` | Complete / review-ready | `docs/milestones/m56-local-adapter-registry-closeout.md` |
| `M57` | Complete / review-ready | `docs/milestones/m57-opt-in-local-text-only-model-harness-closeout.md` |
| `M58` | Complete / review-ready | `docs/milestones/m58-reproducible-local-run-ledger-closeout.md` |

## Boundaries

- No live provider APIs or provider SDKs.
- No local model execution in the deterministic quality gate or release-note generation.
- No live Hermes, OpenClaw, CLI-agent, browser, email, shell, network, or external-action execution.
- No credentials, secrets, private runtime logs, private memory, or private workspace paths.
- No leaderboard or production benchmark claims.

## Sources

- `reports/comparisons/reporting_product_summary.json`
- `reports/comparisons/report_manifest.json`
- `docs/roadmap.md`
- `docs/milestones/m35-openclaw-saved-transcript-pilot-closeout.md`
- `docs/milestones/m36-controlled-live-agent-sandbox-closeout.md`
- `docs/milestones/m37-optional-harness-integration-decision-closeout.md`
- `docs/milestones/m38-reporting-product-layer-closeout.md`
- `docs/milestones/m39-release-notes-reporting-closeout.md`
- `docs/milestones/m40-evidence-quality-audit-closeout.md`
- `docs/milestones/m41-public-safe-transcript-expansion-closeout.md`
- `docs/milestones/m42-scorer-calibration-closeout.md`
- `docs/milestones/m43-historical-trend-snapshots-closeout.md`
- `docs/milestones/m44-optional-non-gated-runtime-trial-closeout.md`
- `docs/milestones/m45-external-fixture-adjudication-coverage-closeout.md`
- `docs/milestones/m46-needs-discussion-resolution-closeout.md`
- `docs/milestones/m47-deterministic-scorer-refinement-triage-closeout.md`
- `docs/milestones/m48-external-fixture-review-expansion-closeout.md`
- `docs/milestones/m49-scorer-candidate-control-tests-closeout.md`
- `docs/milestones/m50-deterministic-scorer-change-decision-closeout.md`
- `docs/milestones/m51-scorer-versioning-guardrails-closeout.md`
- `docs/milestones/m52-focused-scorer-evidence-expansion-closeout.md`
- `docs/milestones/m53-scorer-promotion-or-rubric-update-closeout.md`
- `docs/milestones/m54-local-benchmark-claim-charter-closeout.md`
- `docs/milestones/m55-public-local-benchmark-case-corpus-closeout.md`
- `docs/milestones/m56-local-adapter-registry-closeout.md`
- `docs/milestones/m57-opt-in-local-text-only-model-harness-closeout.md`
- `docs/milestones/m58-reproducible-local-run-ledger-closeout.md`
