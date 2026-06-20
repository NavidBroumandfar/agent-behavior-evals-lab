# Agent Behavior Evals Lab Release Notes

## Summary

| Field | Value |
| --- | --- |
| Generated at | `2026-06-20T00:00:00Z` |
| Release ID | `m39_release_notes_latest` |
| Quality gate command | `python3 scripts/dev.py check` |
| Indexed report artifacts | 17 |
| Baseline pass rate | 91.3% |
| Harness bridge decision | `defer_harness_integration` |

## Highlights

- **Reporting**: Added dashboard-ready JSON, product summary Markdown, and release-note outputs from local artifacts.
- **Quality Gate**: Local deterministic gate remains stable; no live runtime integration is enabled.
- **Harness Boundary**: Harness decision remains defer_harness_integration; runtime-native state required is false.
- **Review**: 12 adjudication records are tracked; 3 still need discussion.

## Dashboard Snapshot

| Metric | Value |
| --- | ---: |
| Baseline records | 126 |
| Baseline failed | 11 |
| External fixture groups | 6 |
| External fixture records | 26 |
| Adjudication records | 12 |
| Review records needing discussion | 3 |

## Milestone Rollup

| Milestone | Status | Closeout |
| --- | --- | --- |
| `M35` | Complete / review-ready | `docs/milestones/m35-openclaw-saved-transcript-pilot-closeout.md` |
| `M36` | Complete / review-ready | `docs/milestones/m36-controlled-live-agent-sandbox-closeout.md` |
| `M37` | Complete / review-ready | `docs/milestones/m37-optional-harness-integration-decision-closeout.md` |
| `M38` | Complete / review-ready | `docs/milestones/m38-reporting-product-layer-closeout.md` |
| `M39` | Complete / review-ready | `docs/milestones/m39-release-notes-reporting-closeout.md` |

## Boundaries

- No live provider APIs or provider SDKs.
- No local model execution.
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
