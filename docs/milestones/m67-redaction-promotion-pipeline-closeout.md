# Milestone 67 - Redaction And Promotion Pipeline

Date: 2026-06-21

Status: Complete / public-safe promotion-pipeline review-ready

Milestone 67 adds a deterministic redaction and promotion pipeline for turning
selected private-evidence metadata into public-safe derivative fixtures. The
committed artifacts use fake M66 private-vault metadata and one synthetic
public-safe promoted output only.

M67 does not ingest private evidence, read raw private artifacts, expose
credentials, expose account data, expose private paths, expose hidden prompts,
commit raw runtime logs, commit real customer data, run live providers, run
local models, execute agents, use browser/email/network tools, perform shell
actions, perform external actions, or add gated LLM review inside
`scripts/dev.py check` or `scripts/check_all.py`.

## Completed Slices

- M67.1 Added `schemas/promotion_candidate.schema.json`.
- M67.2 Added `schemas/redaction_note.schema.json`.
- M67.3 Added a public-safe promotion candidate manifest at `traces/external/redaction_promotion_candidates.example.json`.
- M67.4 Added diffable redaction notes at `traces/external/redaction_notes.example.jsonl`.
- M67.5 Added a public-safe promoted adapter-output derivative at `traces/external/promoted_private_evidence_outputs.example.jsonl`.
- M67.6 Added `src/redaction_promotion_pipeline.py` to validate source-vault metadata, redaction notes, reviewer signoff, promoted-output safety, and report summaries.
- M67.7 Added public-safe summary artifacts at `reports/comparisons/redaction_promotion_pipeline_summary.json` and `reports/comparisons/redaction_promotion_pipeline_summary.md`.
- M67.8 Added deterministic tests for reviewer signoff, redaction-note linkage, raw-value retention rejection, and private-marker rejection.
- M67.9 Wired schema coverage, report manifest coverage, release notes, docs, and `scripts/check_all.py` validation.

## Key Artifacts

Promotion pipeline metadata:

- `traces/external/redaction_promotion_candidates.example.json`
- `traces/external/redaction_notes.example.jsonl`
- `traces/external/promoted_private_evidence_outputs.example.jsonl`
- `schemas/promotion_candidate.schema.json`
- `schemas/redaction_note.schema.json`
- `src/redaction_promotion_pipeline.py`
- `tests/test_redaction_promotion_pipeline.py`

Reports:

- `reports/comparisons/redaction_promotion_pipeline_summary.json`
- `reports/comparisons/redaction_promotion_pipeline_summary.md`

Documentation:

- `docs/wiki/concepts/redaction_promotion_pipeline.md`
- `docs/wiki/reference/schema_validation_coverage.md`
- `docs/live_benchmark_roadmap.md`
- `docs/roadmap.md`

## Pipeline Outcome

- Promotion candidates: 1 fake metadata-backed candidate
- Redaction notes: 1 public-safe field-level redaction note
- Promoted public-safe output records: 1
- Reviewer signoffs: 1
- Private artifacts read by quality gate: false
- Private evidence ingested by quality gate: false
- Public ranking eligible: false

## Evidence Boundary

M67 proves the promotion contract and public-safety checks for a fake private
evidence derivative. It does not prove real redaction quality, private audit
findings, production behavior, runtime safety, public benchmark eligibility, or
leaderboard quality.

The original private artifact remains local-only by contract. The committed
derivative is public-safe promoted evidence, not a public ranking input by
default.

## Quality Gate

From the repository root:

```bash
python3 scripts/dev.py check
```

The gate remains deterministic, local, credential-free, public-safe, and does
not ingest private evidence, read raw private data, handle encryption keys,
execute tools, agents, providers, local models, browser/email/network actions,
shell commands, production-system actions, private memory reads, or external
actions.

## Recommended Next Step

Proceed to M68 Private Audit Reports. Private audit reports should remain
local-only and ignored by Git by default unless a future explicit export path
creates aggregate public-safe outputs.
