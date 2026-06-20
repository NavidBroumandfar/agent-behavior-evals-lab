# Milestone 40 - Evidence Quality Audit

Date: 2026-06-20

Status: Complete / review-ready

Milestone 40 adds a deterministic evidence quality audit across committed local evaluator artifacts.

M40 does not add live provider execution, local model execution, live Hermes or OpenClaw execution, CLI-agent execution, credentials, network collection, browser/email actions, messaging, purchases, file mutation, shell execution, autonomous actions, private runtime-log ingestion, scorer changes, new output collection, or gated LLM review.

## Completed Slices

- M40.1 Added `src/evidence_quality_audit.py` to inventory committed cases, scored traces, fixture manifests, adjudication artifacts, and report metadata.
- M40.2 Added `reports/comparisons/evidence_quality_audit.json`.
- M40.3 Added `reports/comparisons/evidence_quality_audit.md`.
- M40.4 Split evidence gaps into missing fixture coverage, scorer weakness, and reporting weakness.
- M40.5 Added source paths to every audit gap.
- M40.6 Indexed both audit artifacts in `reports/comparisons/report_manifest.json`.
- M40.7 Updated report-manifest expectations, release-note rollup, docs, and wiki references.
- M40.8 Wired audit generation and compile coverage into `scripts/check_all.py`.

## Key Artifacts

Code and tests:

- `src/evidence_quality_audit.py`
- `tests/test_evidence_quality_audit.py`
- `scripts/check_all.py`
- `src/validate_report_manifest.py`
- `tests/test_report_manifest_validation.py`
- `src/release_notes_summary.py`
- `tests/test_release_notes_summary.py`

Generated audit artifacts:

- `reports/comparisons/evidence_quality_audit.json`
- `reports/comparisons/evidence_quality_audit.md`

Docs and manifest:

- `reports/comparisons/report_manifest.json`
- `docs/wiki/concepts/evidence_quality_audit.md`
- `docs/roadmap.md`
- `docs/wiki/index.md`

## Audit Scope

The audit reads only committed local artifacts:

- Eval case JSONL files.
- Baseline scored trace.
- External fixture manifest and scored fixture traces.
- Adjudication manifest and adjudication regression snapshot.
- Report manifest and reporting product summary.
- Harness bridge plan.
- Scorer code and scorer limitation documentation.
- Roadmap.

## Current Evidence Findings

- Eval cases audited: 42
- Total scored records audited: 152
- External fixture records audited: 26
- Adjudication records audited: 12
- Evidence gaps identified: 10
- External fixture scored traces without adjudication coverage: 6

The audit confirms that current external fixtures validate local paths and contracts, but they are still small curated samples. The audit also confirms that adjudication coverage is currently baseline-only and does not yet cover external fixture traces.

## Boundary

The audit does not rank systems, score live target behavior, or make benchmark claims. It identifies evidence quality gaps that should guide M41 transcript expansion, M42 scorer calibration from adjudications, and M43 trend snapshots.

## Quality Gate

From the repository root:

```bash
python3 scripts/dev.py check
```

The gate remains deterministic and local.

## Recommended Next Milestone

Proceed to M41 Public-Safe Transcript Expansion using the M40 gap IDs as source-backed expansion targets.
