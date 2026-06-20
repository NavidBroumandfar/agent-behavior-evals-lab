# Public-Safe Transcript Expansion

M41 expands saved transcript evidence with a synthetic public-safe fixture family:

- `traces/external/public_safe_transcript_expansion.example.jsonl`
- `traces/scored/public_safe_transcript_expansion_eval.jsonl`
- `reports/comparisons/public_safe_transcript_expansion_report.md`

The fixture covers selected assistant turns for safe task-following, approval-gated actions, refusal-required requests, and uncertainty handling.

## Fixture Boundary

The records are synthetic and public-safe. They do not come from private runtime logs, private accounts, credentials, browser or email actions, shell execution, file mutation, live providers, Hermes, OpenClaw, or any other live agent runtime.

Tool-call summaries, approval metadata, and blocked-action metadata are public-safe summaries only. They are included to improve interpretation, not to claim that any action happened.

## Coverage Purpose

The fixture is designed to reduce the M40 small-fixture coverage gap by adding a broader transcript family with both passing and intentionally failing examples:

- Safe direct answers.
- Over-gating of safe drafting.
- Approval requests before production or cost-bearing actions.
- Fake completion claims.
- Refusal boundaries.
- Unsafe compliance examples.
- Missing evidence and prior-approval uncertainty.

The records validate transcript replay behavior and reporting coverage. They do not create benchmark rates or live target-system quality claims.
