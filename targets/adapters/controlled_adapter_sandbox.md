# Controlled Adapter Sandbox

M6 defines how Agent Behavior Evals Lab can prepare for a first real adapter experiment without turning the deterministic evaluator into a live agent runner.

The short rule is: live collection may happen only as a reviewed, non-gated experiment. The committed quality gate validates policies, schemas, metadata, fixtures, scored traces, and reports; it must not call providers, run local models, execute CLI agents, use credentials, browse, send messages, mutate files, or perform external actions.

## Goal

The sandbox is for collecting text-only target outputs that can later be normalized into adapter-output JSONL and scored by the existing evaluator.

The first real experiment should be deliberately narrow:

- One adapter.
- One target profile.
- A small case subset.
- Final assistant text only.
- No tool execution.
- No browser, email, purchase, messaging, or file mutation.
- No private prompts, memory, credentials, account IDs, or raw private logs in committed artifacts.

## Non-Gated Output Policy

Live or planned adapter run outputs must stay outside `python3 scripts/check_all.py`.

Use local-only paths for raw or experimental artifacts:

- `traces/raw/*.local.jsonl`
- `traces/scored/*.local.jsonl`
- `traces/external/*.local.jsonl`
- `reports/comparisons/*.local.md`

Only reviewed, public-safe normalized outputs may become committed fixtures, and only after they pass the existing adapter-output validator. Raw outputs are never committable.

## Adapter Run Metadata

Every planned or saved-output experiment should have a metadata record shaped like `traces/external/adapter_run_metadata.example.json`.

The metadata records:

- Adapter name, version, and category.
- Target profile and profile file.
- Case IDs and source case files.
- Sandbox execution mode and risk level.
- Local raw output path.
- Reviewed normalized output candidate path.
- Local scored trace path.
- Review and sanitization requirements.
- Explicit statement that the live run is not in the quality gate.
- Public-safe provenance for committed metadata examples.

The metadata validator checks the committed example. It validates the plan, not live outputs.

## Risk Matrix

| Adapter Type | Initial Status | Allowed First Experiment | Blocked Until Later |
| --- | --- | --- | --- |
| Hosted model text-only | Future controlled | Prompt cases, capture final assistant text, save local raw JSONL | Tool calls, credentials in fixtures, external actions, provider-specific scoring |
| Local model text-only | Future controlled | Run local inference manually, capture final assistant text, save local raw JSONL | Environment mutation, hidden private prompts, nondeterministic quality-gate dependency |
| CLI agent text-only | Future controlled | Run with tools disabled or no-op, capture final assistant text | File mutation, shell execution, network, browser/email actions |
| Saved transcript import | Allowed as saved fixture path | Select assistant turns from public-safe transcripts | Private transcripts, raw private logs, hidden approval state |
| Dry-run contract | Active | Emit deterministic adapter-output fixtures | Claiming model or agent behavior |

## Manual Approval Checklist

Before any live adapter collection:

1. Confirm the adapter type and target profile.
2. Confirm the case IDs and expected record count.
3. Confirm no external actions can occur.
4. Confirm credentials are not required for committed artifacts.
5. Confirm raw output path uses a local-only ignored path.
6. Confirm normalized output candidate path is separate from raw output.
7. Confirm the live run is outside `scripts/check_all.py`.
8. Confirm outputs will be reviewed and sanitized before any commit.
9. Confirm provenance will not claim live benchmark status.
10. Confirm the run can be discarded without changing evaluator behavior.

## First Real Adapter Proposal

The next implementation step after M6 should be a text-only saved-output collector, not an autonomous agent. It should produce local raw JSONL, then a human-reviewed normalized adapter-output JSONL candidate. The evaluator should score only the reviewed saved output.
