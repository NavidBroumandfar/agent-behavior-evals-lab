# Private Audit Reports

Private audit reports are local-only reports generated from private evidence
metadata. They are for maintainer-side audit review, not public benchmark
publication.

M68 adds the report contract and generator. The committed example uses fake
public-safe metadata only.

## Report Label

Any report generated from private evidence must be labeled
`private_audit_report`.

The label is required in the report metadata fixture, copied into the generated
local JSON report, and checked by the deterministic quality gate.

## Local Output Boundary

Private audit JSON and Markdown reports default to ignored local paths:

- `reports/private/m68_private_audit_report.local.json`
- `reports/private/m68_private_audit_report.local.md`

The `reports/private/` root is ignored by Git. The quality gate can generate
fake-metadata local reports there, but committed report artifacts remain under
`reports/comparisons/` and contain aggregate public-safe boundary summaries.

## Metadata Contract

`schemas/private_audit_report.schema.json` validates:

- source vault manifest linkage,
- required `private_audit_report` label,
- ignored private report output defaults,
- aggregate-only public export policy,
- quality-gate exclusions,
- safety assertions,
- section boundaries that forbid raw private values.

The committed metadata request at
`traces/external/private_audit_report_metadata.example.json` references the M66
fake private evidence vault manifest and selects fake record IDs only.

## Aggregate Export Boundary

Public summaries are aggregate-only and public-safe by default. They can report
counts by source runtime, source kind, retention class, and redaction status,
but they do not include raw private evidence, credentials, private workspace
paths, real customer data, or private artifact paths.

Aggregate export is not enabled by default for real private evidence. It must
remain public-safe and avoid per-record private details.

## Quality-Gate Boundary

`python3 scripts/dev.py check` validates M68 using fake metadata only. It does
not ingest private evidence, read raw private logs, handle credentials or
secrets, call providers, run models, execute Hermes, OpenClaw, production
systems, browser/email/network/shell actions, external actions, or gated LLM
review.

Private audit reports do not create public leaderboard evidence, production
safety proof, third-party reproducibility evidence, or broader private-audit
claims.
