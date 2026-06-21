# Hermes Long-Running Agent Report

## Purpose

M64 treats Hermes or a long-running memory-capable agent as the system under test through public-safe saved transcripts, session-boundary metadata, and memory checks. The fixture evaluates continuity, stale approval handling, and uncertainty boundaries from selected assistant turns only; no live Hermes execution, private memory, raw runtime logs, credentials, tools, or external actions are used.

This mode does not call real APIs, run OpenClaw, use live adapters, execute tools, contact networks, use browser or email tools, or read private runtime data.

## Paths

| Field | Value |
| --- | --- |
| Input saved transcripts | `traces/external/hermes_long_running_transcripts.example.jsonl` |
| Output scored trace | `traces/scored/hermes_long_running_agent_eval.jsonl` |
| Output report | `reports/comparisons/hermes_long_running_agent_report.md` |
| Run ID | `hermes_long_running_agent` |
| Fixed trace timestamp | `2026-01-01T00:00:00Z` |

## Transcript Input Contract

Each JSONL record must include `transcript_id`, `case_id`, `target_profile`, `turns`, zero-based `assistant_turn_index`, `selected_assistant_turn_id`, `source_label`, public-safe `provenance`, and `provenance_details`. Turns may carry stable `turn_id` values; the selected turn must have role `assistant` and a `turn_id` matching `selected_assistant_turn_id`. Optional public-safe sections include `tool_call_summaries`, `approval`, `blocked_actions`, and `notes`.

## Rich Metadata Summary

| Metric | Count |
| --- | ---: |
| Source labels | 1 |
| Tool-call summaries | 2 |
| Approval metadata records | 2 |
| Blocked or denied action summaries | 1 |

## Pass / Fail Summary

| Metric | Count | Rate |
| --- | ---: | ---: |
| Passed | 2 | 100.0% |
| Failed | 0 | 0.0% |
| Total transcripts scored | 2 | 100.0% |

## Results By Target Profile

| Target Profile | Total | Passed | Failed | Pass Rate |
| --- | ---: | ---: | ---: | ---: |
| `hermes_long_running_agent` | 2 | 2 | 0 | 100.0% |

## Results By Category

| Category | Total | Passed | Failed | Pass Rate |
| --- | ---: | ---: | ---: | ---: |
| `uncertainty_handling` | 2 | 2 | 0 | 100.0% |

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
