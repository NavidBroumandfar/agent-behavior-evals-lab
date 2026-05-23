# Profile Comparison Report

## Data Source

| Field | Value |
| --- | --- |
| Input trace | `traces/scored/baseline_mock_run.jsonl` |
| Output report | `reports/comparisons/profile_comparison_report.md` |
| Run ID | `baseline_mock_run` |
| Total scored records | 90 |
| Profiles compared | `generic_assistant`, `openclaw_reference_agent`, `strict_approval_agent` |
| Categories compared | `safe_direct_response`, `approval_gated`, `refusal_required`, `uncertainty_handling` |
| Trace timestamp range | `2026-01-01T00:00:00Z` |

## Overall Profile Comparison

| Profile | Total | Passed | Failed | Pass Rate | Comparison Note |
| --- | ---: | ---: | ---: | ---: | --- |
| `generic_assistant` | 30 | 25 | 5 | 83.3% | Useful direct-answer baseline; intentionally weaker on approval-gated cases in this mock trace. |
| `openclaw_reference_agent` | 30 | 30 | 0 | 100.0% | Simulated reference profile with disciplined gating and uncertainty behavior; not a live OpenClaw runtime result. |
| `strict_approval_agent` | 30 | 27 | 3 | 90.0% | Conservative approval-focused profile; strong on gates but intentionally prone to over-gating safe tasks. |

## Pass/Fail By Profile

| Profile | Passed | Failed | Total |
| --- | ---: | ---: | ---: |
| `generic_assistant` | 25 | 5 | 30 |
| `openclaw_reference_agent` | 30 | 0 | 30 |
| `strict_approval_agent` | 27 | 3 | 30 |

## Pass Rate By Profile And Category

| Profile | `safe_direct_response` | `approval_gated` | `refusal_required` | `uncertainty_handling` |
| --- | ---: | ---: | ---: | ---: |
| `generic_assistant` | 10/10 (100.0%) | 5/10 (50.0%) | 5/5 (100.0%) | 5/5 (100.0%) |
| `openclaw_reference_agent` | 10/10 (100.0%) | 10/10 (100.0%) | 5/5 (100.0%) | 5/5 (100.0%) |
| `strict_approval_agent` | 7/10 (70.0%) | 10/10 (100.0%) | 5/5 (100.0%) | 5/5 (100.0%) |

## Failure Modes By Profile

| Profile | `missing_approval_gate` | `over_refusal` | Total Failure Labels |
| --- | ---: | ---: | ---: |
| `generic_assistant` | 5 | 0 | 5 |
| `openclaw_reference_agent` | 0 | 0 | 0 |
| `strict_approval_agent` | 0 | 3 | 3 |

## Notable Behavior Tradeoffs

- `generic_assistant` has 5 `missing_approval_gate` failures, showing the shaped baseline weakness on consequential-action gating.
- `openclaw_reference_agent` has 0 failures in this deterministic mock trace, but this is a simulated reference profile rather than live OpenClaw evidence.
- `strict_approval_agent` has 3 `over_refusal` failures, showing the tradeoff between conservative gating and direct handling of safe requests.

## Interpretation

This is a deterministic mock comparison, not a real model benchmark. The mock client is intentionally shaped to validate the evaluator's trace, scoring, aggregation, and reporting logic.

No live OpenClaw execution happened. The `openclaw_reference_agent` profile is simulated and should be read as a reference behavior target, not as an active runtime result.

The comparison is useful for validating behavior-tradeoff interpretation: the generic profile exposes approval-gate misses, the strict approval profile exposes over-gating on safe tasks, and the simulated reference profile provides a clean comparator for report mechanics.

## Known Limitations

- Results come from deterministic mock outputs, not live model or agent responses.
- The scorer is v0 heuristic-based and intentionally simple.
- Profile differences are shaped test signals, not measured production behavior.
- The report compares one baseline trace and does not yet compare previous-vs-current runs.
- No real model adapters, live OpenClaw execution, network calls, browser actions, email actions, or autonomous actions are involved.

## Next Improvements

- Add more reviewer adjudication fixtures for cases where the v0 heuristic scorer is too coarse.
- Add unresolved `needs_discussion` reporting and optional review-coverage thresholds.
- Add support for multiple adjudication fixture families.
- Add promotion status reporting for reviewed text-only output candidates once they become committed fixtures.
- Add shared report-table helpers to reduce duplication across comparison reports.
- Keep manifest-driven fixture comparison as the source of truth for external fixture groups.
- Keep comparison outputs general enough for future text-only model and agent adapters.
