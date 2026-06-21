# Retention Consent Access Summary

## Summary

This M69 summary is public-safe fake metadata only. It validates retention, consent, access-control, deletion, and export boundaries without reading private evidence or performing private actions.

| Field | Value |
| --- | --- |
| Generated at | `2026-06-22T00:00:00Z` |
| Source metadata | `traces/external/retention_consent_access_metadata.example.json` |
| Source vault manifest | `traces/external/private_evidence_vault_manifest.example.json` |
| Source private audit metadata | `traces/external/private_audit_report_metadata.example.json` |
| Fake metadata only | `true` |
| Retention-control records | 2 |
| Authorization required | 2 |
| Private artifacts read | `false` |
| Deletion actions executed | `false` |
| Private artifact exports executed | `false` |

## Evidence Age

| Metric | Value |
| --- | ---: |
| Oldest fake evidence age days | 41 |
| Newest fake evidence age days | 21 |
| Average fake evidence age days | 31.0 |

## Access Boundary

- Vault root ignored: `true`
- Private report root ignored: `true`
- Local store access: `local_maintainer_workstation_only`
- Required role: `authorized_local_auditor`
- Shared storage allowed: `false`
- Private audit report label: `private_audit_report`

## Deletion And Export Boundary

- Delete targets limited to ignored private roots: `true`
- Deletion command in quality gate: `false`
- Private artifact export enabled by default: `false`
- Public-safe aggregate export enabled: `true`
- Per-record private details in aggregate export: `false`

## Aggregate Counts

- Retention classes: `{'delete_after_review': 1, 'retain_local_until_manually_deleted': 1}`
- Retention actions: `{'delete_after_review_window': 1, 'manual_delete_review_required': 1}`
- Authorization statuses: `{'authorization_required_not_embedded': 2}`
- Access boundaries: `{'local maintainer workstation only': 2}`

## Boundaries

- Committed M69 summaries are aggregate-only and public-safe.
- The deterministic gate validates fake metadata only and does not read raw private evidence.
- Deletion and private artifact export boundaries are validated as metadata; no deletion or export action is executed.
- Private evidence and private audit report roots remain ignored by Git and local-only by default.
- Consent or authorization proof is not embedded in committed fixtures.
- Evidence age and access-boundary reporting uses fake collected-at metadata and aggregate counts only.
- M69 does not create public leaderboard evidence, production-safety proof, third-party reproducibility evidence, or private-audit overclaims.
