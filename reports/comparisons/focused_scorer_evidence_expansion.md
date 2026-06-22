# Focused Scorer Evidence Expansion

## Summary

| Field | Value |
| --- | ---: |
| Generated at | `2026-06-21T00:00:00Z` |
| Focused controls | 6 |
| Candidate groups | 2 |
| Review/scorer result mismatches | 1 |
| Accepted scorer changes | 0 |
| Scorer code changed | false |
| Scored trace behavior changed | false |
| Decision | `evidence_expanded_no_scorer_change` |

M52 expands focused public-safe evidence but keeps the deterministic scorer unchanged. The new records improve reviewer coverage around the current candidates; any future scorer change still needs a separate deterministic promotion step with tests, regenerated affected traces, and historical adjudication context.

## Fixture

| Metric | Value |
| --- | ---: |
| Source records | 6 |
| Scored trace records | 6 |
| Adjudication records | 6 |
| Current calibration records | 80 |
| Current changed results | 3 |

## Candidate Evidence

| Candidate | Records | Mismatches | Decisions | Source Adjudications |
| --- | ---: | ---: | --- | --- |
| `triage_review_safe_clarification_vs_over_refusal` | 3 | 0 | `uphold_score`=3 | `ADJ-M52-FOCUSED-SAFE-004-STRICT-001`, `ADJ-M52-FOCUSED-SAFE-009-STRICT-001`, `ADJ-M52-FOCUSED-SAFE-012-GENERIC-001` |
| `triage_strengthen_approval_risk_disclosure_review` | 3 | 1 | `override_fail`=1, `uphold_score`=2 | `ADJ-M52-FOCUSED-APPROVAL-003-GENERIC-001`, `ADJ-M52-FOCUSED-APPROVAL-007-GENERIC-001`, `ADJ-M52-FOCUSED-APPROVAL-011-OPENCLAW-001` |

## Required Follow-Up

| Follow-Up | Phase | Summary |
| --- | --- | --- |
| `decide_future_scorer_promotion_or_rubric_update` | `M53` | Use M49 controls, M50 no-change rationale, M51 guardrails, and M52 focused evidence to decide whether a later deterministic scorer or rubric update is justified. |

## Boundary

- Focused evidence is committed public-safe saved text and reviewed adjudication metadata.
- Reviewer decisions remain separate from heuristic scored traces.
- No scorer code changes are accepted in M52.
- No scored trace behavior changes are introduced in M52.
- No live provider, local model, runtime, network, private data, credential, browser/email, shell, file mutation, or external action is introduced.

## Sources

- `traces/external/focused_scorer_evidence.example.jsonl`
- `traces/scored/focused_scorer_evidence_eval.jsonl`
- `traces/external/focused_scorer_evidence_adjudications.example.jsonl`
- `reports/comparisons/scorer_change_decision.json`
- `reports/comparisons/scorer_versioning_guardrails.json`
- `reports/comparisons/scorer_calibration_summary.json`
- `src/scorers.py`
