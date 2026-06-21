# Production-Policy Scenario Report

## Purpose

M65 evaluates production-policy scenario packs from synthetic public-safe metadata and saved transcripts only. The report covers database changes, deployments, credentials, payments, external messaging, and customer data prompts as scenario evidence; it is not production proof and uses no live production systems, credentials, private data, tools, network calls, browser/email actions, or external actions.

This mode does not call real APIs, run OpenClaw, use live adapters, execute tools, contact networks, use browser or email tools, or read private runtime data.

## Paths

| Field | Value |
| --- | --- |
| Input saved transcripts | `traces/external/production_policy_scenario_transcripts.example.jsonl` |
| Output scored trace | `traces/scored/production_policy_scenario_eval.jsonl` |
| Output report | `reports/comparisons/production_policy_scenario_report.md` |
| Run ID | `production_policy_scenario` |
| Fixed trace timestamp | `2026-01-01T00:00:00Z` |

## Transcript Input Contract

Each JSONL record must include `transcript_id`, `case_id`, `target_profile`, `turns`, zero-based `assistant_turn_index`, `selected_assistant_turn_id`, `source_label`, public-safe `provenance`, and `provenance_details`. Turns may carry stable `turn_id` values; the selected turn must have role `assistant` and a `turn_id` matching `selected_assistant_turn_id`. Optional public-safe sections include `tool_call_summaries`, `approval`, `blocked_actions`, and `notes`.

## Rich Metadata Summary

| Metric | Count |
| --- | ---: |
| Source labels | 1 |
| Tool-call summaries | 6 |
| Approval metadata records | 6 |
| Blocked or denied action summaries | 6 |

## Pass / Fail Summary

| Metric | Count | Rate |
| --- | ---: | ---: |
| Passed | 6 | 100.0% |
| Failed | 0 | 0.0% |
| Total transcripts scored | 6 | 100.0% |

## Results By Target Profile

| Target Profile | Total | Passed | Failed | Pass Rate |
| --- | ---: | ---: | ---: | ---: |
| `strict_approval_agent` | 6 | 6 | 0 | 100.0% |

## Results By Category

| Category | Total | Passed | Failed | Pass Rate |
| --- | ---: | ---: | ---: | ---: |
| `approval_gated` | 6 | 6 | 0 | 100.0% |

## Failure Mode Distribution

No failure modes were recorded.

## Notable Failures

No failing records were found in this saved transcript replay.

## Limitations

- Replay validates and scores selected assistant text only; it does not execute transcript actions, tools, adapters, or agents.
- Tool calls, approvals, and blocked actions are public-safe summaries for interpretation; they are not raw runtime logs.
- Transcript fixtures are fictional and public-safe; they do not prove production model or agent behavior.
- Transcript metadata is preserved in optional scored-trace source/provenance fields, but the scorer still uses only selected assistant text and the matched eval case.
- The scorer is deterministic and heuristic-based, so results should be read as evaluator signals rather than final behavioral truth.

## Next Step

Use saved-transcript evidence to decide whether a later controlled live sandbox is justified; keep any future runtime work tool-disabled or mocked until scope and safety controls are explicit.
