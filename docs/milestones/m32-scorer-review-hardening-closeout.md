# Milestone 32 - Scorer And Review Hardening

Date: 2026-06-20

Status: Complete / review-ready

Milestone 32 hardens the deterministic v0 scorer and reviewer guidance without changing the evaluator boundary.

M32 does not add live provider calls, local model execution, CLI agent execution, credentials, network collection, browser/email actions, autonomous actions, gated LLM review, or real adapter execution inside the deterministic quality gate.

## Completed Slices

- M32.1 Added targeted scorer tests for the M31 agent-risk families: production migrations, credential rotation, invoice/payment email, release deployment, credential exfiltration, audit-log evasion, deceptive monitoring, uploaded logs, prior approvals, production command context, safe shell-command review, and safe file-permission explanation.
- M32.2 Improved refusal-required heuristic coverage for mixed-refusal responses that still provide explicit M31-style credential exfiltration, audit-evasion, payroll-tampering, or deceptive-monitoring instructions.
- M32.3 Documented known v0 scorer false positives and false negatives in `docs/wiki/concepts/v0_scorer_limitations.md`.
- M32.4 Added reviewer override guidance to `docs/wiki/concepts/human_adjudications.md`.
- M32.5 Updated the roadmap and wiki index for M32.

## Key Artifacts

Code and tests:

- `src/scorers.py`
- `tests/test_scorers.py`

Docs:

- `docs/wiki/concepts/v0_scorer_limitations.md`
- `docs/wiki/concepts/human_adjudications.md`
- `docs/roadmap.md`
- `docs/wiki/index.md`

## Scorer Boundary

The v0 scorer remains deterministic, local, and standard-library only. It still uses transparent phrase and pattern checks over saved output text.

The scorer change is intentionally narrow: it catches refusal-required outputs that refuse in one clause but still give explicit instructions such as searching for API keys, disabling audit logging, changing payroll records, or using a fake security alert to install monitoring.

## Review Boundary

Reviewer adjudications remain a report-time layer over scored traces. Overrides do not mutate source traces, rewrite regression snapshots, rescore outputs, or train an automatic judge.

The documented guidance recommends:

- `override_pass` for clear heuristic false positives.
- `override_fail` for clear heuristic false negatives.
- `needs_discussion` when reviewer calibration or fixture context is insufficient.

## Reports And Snapshots

M32 is not intended to change the committed baseline mock output aggregates. Reports and regression snapshots should only be regenerated if verification shows that scorer behavior changed for existing committed trace inputs.

## What Remains Intentionally Blocked

- Live model or agent evaluation.
- Provider SDKs, credentials, or network collection.
- Browser, email, messaging, purchase, or file-mutation actions.
- Gated LLM-assisted judging.
- Applying adjudications back to source traces.
- Treating deterministic mock results as production model evidence.

## Quality Gate

From the repository root:

```bash
python3 scripts/dev.py check
```

The gate remains deterministic and local.

## Recommended Next Milestone

Milestone 33 should add the first controlled real text-only adapter path for reviewed final text only. It should keep raw outputs local-only, require public-safe normalized fixtures before scoring, and keep live collection outside the deterministic quality gate.
