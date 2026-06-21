# Private Audit Report Boundary Summary

## Summary

This M68 summary is public-safe fake metadata only. The generated private audit report defaults to ignored local paths; committed artifacts remain aggregate-only.

| Field | Value |
| --- | --- |
| Generated at | `2026-06-21T00:00:00Z` |
| Source metadata | `traces/external/private_audit_report_metadata.example.json` |
| Report label | `private_audit_report` |
| Private report root | `reports/private/` |
| Private reports committable | `false` |
| Private outputs written | `true` |
| Included private record metadata | 2 |
| Promotion candidates | 1 |
| Reviewer signoffs | 0 |
| Private artifacts read | `false` |
| Public leaderboard eligible | `false` |

## Aggregate Export Boundary

- Enabled by default: `false`
- Public-safe by default: `true`
- Aggregate only: `true`
- Per-record private details in export: `false`

## Boundaries

- Committed M68 summaries are aggregate-only and public-safe.
- Local private audit JSON/Markdown outputs are generated under the ignored reports/private/ root by default.
- Reports generated from private evidence must be labeled private_audit_report.
- The deterministic gate uses fake metadata only and does not ingest or read raw private evidence.
- No credentials, secrets, private workspace paths, real customer data, live execution, provider calls, browser/email/network/shell actions, external actions, or gated LLM review are introduced.
- Private audit reports do not make public leaderboard, production-safety, third-party reproducibility, or private-audit overclaims.
