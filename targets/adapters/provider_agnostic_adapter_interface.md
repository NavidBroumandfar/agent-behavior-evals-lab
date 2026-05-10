# Provider-Agnostic Adapter Interface

This document defines the future adapter interface for Agent Behavior Evals Lab. It is design and contract work only. It does not implement live adapters, provider SDKs, local model execution, OpenClaw execution, browser/email tools, network calls, credentials, or private runtime integration.

The evaluator should not know or care whether saved outputs came from a hosted model, local model, saved transcript, CLI agent, OpenClaw-style fixture, dry-run adapter, or future controlled adapter. The evaluator consumes normalized adapter-output records and applies the same validation, import, scoring, trace, and report pipeline.

## Purpose

Adapters are target-side producers of saved outputs. Their job is to collect, receive, or synthesize final assistant/model text from a target system and normalize that text into the public adapter-output record contract.

The adapter interface exists to keep the evaluator provider-agnostic:

- Cases remain evaluator-owned.
- Scoring remains evaluator-owned.
- Trace writing remains evaluator-owned.
- Reports remain evaluator-owned.
- Target-specific collection, runtime calls, transcript selection, and source metadata stay outside the scorer.

If two adapters produce the same normalized adapter-output record, the evaluator should score them the same way.

## Non-Goals

M4.5 does not add:

- Live provider APIs.
- Provider SDKs or provider-specific code.
- Local model execution.
- Live OpenClaw CLI execution.
- Browser, email, messaging, purchase, file mutation, or other external actions.
- Credentials, secrets, tokens, private account metadata, or private runtime integration.
- A real adapter implementation.
- Scoring changes.
- New eval cases.

## Evaluator-Side Boundary

The evaluator owns deterministic interpretation:

1. Load eval cases from `evals/cases/*.jsonl`.
2. Validate normalized adapter-output JSONL with `src/validate_adapter_outputs.py`.
3. Import validated records with `src/import_adapter_outputs.py`.
4. Apply `src/scorers.py` to `output_text` and the matched eval case.
5. Validate scored traces against `schemas/trace.schema.json`.
6. Write scored traces in `traces/scored/`.
7. Generate comparison and inspection reports.

The evaluator should not branch on provider, model family, OpenClaw, local runtime, CLI agent, transcript source, or adapter implementation.

## Target-Side Boundary

Adapters own target-side collection and normalization:

- Accept or map an eval case.
- Preserve the eval `case_id`.
- Choose a supported `target_profile`.
- Capture or provide final assistant/model text as `output_text`.
- Emit a normalized adapter-output record.
- Preserve deterministic ordering and stable `record_id` values.
- Include public-safe provenance and metadata.
- Avoid hiding live execution behind fixture labels.
- Avoid claiming tool use, external actions, or completed actions unless captured evidence supports the claim.
- Keep secrets, private prompts, private memory, raw private runtime logs, and credentials out of public fixtures.

## Required Output Record

Each adapter output must normalize to the record contract documented by `schemas/adapter_output.schema.json` and enforced by `src/validate_adapter_outputs.py`.

Required fields:

- `record_id`: stable record identifier.
- `case_id`: existing eval case identifier.
- `target_profile`: evaluated target/profile label compatible with scored traces.
- `source_type`: source category.
- `adapter_name`: stable adapter identifier.
- `created_at`: UTC timestamp string ending in `Z`; committed fixtures use fixed timestamps.
- `output_text`: final assistant/model text to score.
- `provenance`: public-safe provenance object.

Optional fields:

- `adapter_version`: public adapter version label.
- `metadata`: public-safe deterministic source metadata.

## Source Types

Current saved fixture source types:

- `dry_run_adapter_output`
- `manual_adapter_output`
- `saved_adapter_output`
- `saved_transcript_output`

Future source types may be added later for controlled provider, local model, CLI agent, or OpenClaw-style output. Future live source types must be explicit in schema/docs, must not masquerade as saved fixture labels, and must remain outside the deterministic quality gate unless a later milestone explicitly changes that boundary.

## Adapter Output Lifecycle

The provider-agnostic lifecycle is:

1. Target-side generation or selection happens outside the scorer.
2. Adapter writes normalized adapter-output JSONL.
3. `src/validate_adapter_outputs.py` validates shape and provenance.
4. `src/import_adapter_outputs.py` joins records to eval cases and imports them.
5. Existing scorer produces scored trace records.
6. Comparison and reporting scripts summarize already-scored traces.

This lifecycle lets future adapters change how outputs are collected without changing how outputs are scored.

## Provenance Expectations

Every record must include:

- `public_safe`: whether the record is safe for the public repository.
- `live_execution`: whether a live target system was executed.
- `external_actions`: whether browser, email, messaging, purchase, file mutation, or other external actions occurred.
- `contains_private_data`: whether private user data, credentials, secrets, private paths, or private runtime data are present.

M4 fixtures require:

```json
{
  "public_safe": true,
  "live_execution": false,
  "external_actions": false,
  "contains_private_data": false
}
```

Later milestones may add provider/model/runtime metadata such as public model labels, public adapter configuration labels, transcript IDs, selected turn IDs, or controlled run IDs. Credentials, secrets, account identifiers, private workspace paths, raw private logs, and private prompts must never be committed.

## Adapter Categories

These are design categories only:

- Dry-run fixture adapter: deterministic local contract test; active as `src/dry_run_adapter.py`.
- Manual output adapter: reviewer-provided saved text.
- Saved transcript adapter: selected assistant turns from public-safe transcript fixtures.
- Hosted model adapter: future only; live collection outside the deterministic gate.
- Local model adapter: future only; local runtime collection outside the deterministic gate.
- CLI agent adapter: future only; controlled collection with explicit safety boundaries.
- OpenClaw-style adapter: future only and controlled; OpenClaw remains one possible system under test, not the evaluator's purpose.

## Approval And Safety Boundary

Live execution must remain outside `python3 scripts/check_all.py` unless a future milestone explicitly changes that rule.

External actions require separate approval and governance. They are not part of M4.5. A future adapter must not send messages, browse, make purchases, mutate files, change settings, submit forms, or execute CLI agent actions as part of deterministic public fixtures.

Credentials must never enter public fixtures. Private runtime outputs must not be committed. If live collection is added later, raw collection artifacts should be reviewed and sanitized before any public fixture is produced.

## Determinism

Committed fixtures must be deterministic:

- Fixed timestamps.
- Stable record ordering.
- Stable record IDs.
- Stable output text.
- No random behavior.
- No current-time calls.
- No network dependency.

Future live output may be nondeterministic during collection. That collection should produce reviewed saved artifacts separately from deterministic quality-gate fixtures.

## Preparation For Later Implementation

M4.1 through M4.4 already establish the path:

- M4.1 validates normalized adapter-output records.
- M4.2 imports validated records into scored traces.
- M4.3 compares already-scored external fixture groups.
- M4.4 proves a deterministic no-network dry-run adapter can emit records for that path.

M4.5 names the interface future real adapters must satisfy. Later implementation can add controlled adapters by making them emit the same normalized records first, then using the existing validator/importer/scorer/report pipeline without provider-specific scoring logic.
