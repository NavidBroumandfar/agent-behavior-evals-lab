# External Fixture Adjudication Coverage

M45 adds reviewer coverage for selected committed public-safe external fixture traces.

The new fixture is:

- `traces/external/external_fixture_adjudications.example.jsonl`

It is registered in:

- `traces/external/adjudication_manifest.json`

## Reviewed Source Traces

The M45 fixture reviews records from:

- `traces/scored/public_safe_transcript_expansion_eval.jsonl`
- `traces/scored/adapter_output_fixture_import.jsonl`

These are already committed scored traces. The adjudications do not rewrite them.

## What It Improves

Before M45, committed adjudications covered the baseline mock trace only. M45 expands review coverage to two external fixture traces:

- Public-safe saved transcript expansion records.
- Normalized adapter-output fixture records.

This gives scorer calibration, evidence audits, product summaries, and trend snapshots more than one source trace to summarize.

## Boundaries

External fixture adjudications are report-time reviewer records. They do not:

- Run providers, local models, Hermes, OpenClaw, CLI agents, browser tools, email tools, shell commands, or external actions.
- Collect private logs, private memory, credentials, or raw runtime outputs.
- Change scorer behavior.
- Rewrite scored traces.
- Promote raw local output into the quality gate.

Reviewer decisions stay separate from heuristic results in adjudication reports, regression snapshots, calibration summaries, and trend artifacts.
