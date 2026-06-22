# M91 Approval-Gate Pass Review Closeout

Status: complete / review-ready.

M91 converts the post-M90 review coverage priority recommendation into a
committed public-safe adjudication fixture. The batch reviews high-severity
approval-gated heuristic passes for false-negative risk without changing the
deterministic scorer.

## Scope

- Added `traces/external/m91_approval_gate_pass_adjudications.example.jsonl`
  with 20 public-safe adjudications.
- Reviewed high-severity approval-gated pass records from
  `traces/scored/baseline_mock_run.jsonl`.
- Upheld 17 OpenClaw-reference or strict-approval pass records.
- Recorded three reviewer `override_fail` decisions for generic approval
  responses that ask for confirmation but omit target-specific risk, scope,
  impact, or reversibility details.
- Updated `traces/external/adjudication_manifest.json` to include the M91
  fixture as a quality-gate adjudication family.
- Added independent M91 adjudication validation to `scripts/check_all.py`.
- Regenerated deterministic adjudication, scorer reliability, review coverage,
  reporting product, evidence audit, historical trend, and release-note
  artifacts.

## Boundary

- The deterministic heuristic scorer remains the quality-gate scorer.
- M91 does not change scored traces, rewrite model outputs, or promote scorer
  changes.
- M91 uses only committed public-safe fixtures and reports.
- No provider calls, local model calls, Hermes or OpenClaw execution,
  credentials, browser/email actions, production actions, or external actions
  are introduced.

## Result

- Committed adjudication coverage rises from 80 to 100 records.
- Unreviewed heuristic failures remain at zero.
- Approval-gate review coverage increases, and the scorer reliability reports
  now reflect three additional false-negative signals for generic approval
  disclosures that were too vague.

## Next Reviewer Work

After M91, the next deterministic review phase should continue sampling the
remaining unreviewed high-severity approval-gated passes before moving to
medium-severity approval or uncertainty records.
