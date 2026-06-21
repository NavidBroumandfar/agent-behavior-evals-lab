# Private Evidence Vault Boundary Summary

## Summary

This M66 report is public-safe fake metadata only. It validates local private evidence vault boundaries; it is not a private audit report and does not include private evidence.

| Field | Value |
| --- | --- |
| Generated at | `2026-06-21T00:00:00Z` |
| Source manifest | `traces/external/private_evidence_vault_manifest.example.json` |
| Evidence class | `private_audit_metadata_public_safe` |
| Fake metadata only | `true` |
| Private record metadata count | 2 |
| Promotion candidates | 1 |
| Promotion allowed | 0 |

## Vault Controls

| Control | Value |
| --- | --- |
| Vault root | `private_evidence/` |
| Vault root ignored | `true` |
| Private report root | `reports/private/` |
| Private report root ignored | `true` |
| Raw private records committable | `false` |
| Private reports committable | `false` |

## Storage Plan

- Storage mode: `ignored_local_directory`
- Encryption plan: `optional_local_file_encryption_or_os_keychain_wrapped_key`
- Encryption required for real private evidence: `true`
- Key material committable: `false`
- Secret material in manifest: `false`

## Private Audit Report Label

- Required label: `private_audit_report`
- Reports generated from private evidence marked private audit: `true`
- Public leaderboard eligible: `false`

## Boundaries

- The deterministic gate validates fake metadata only.
- Raw private evidence and private audit reports stay under ignored local paths by default.
- M66 does not promote private records; promotion is blocked until explicit redaction metadata and a future M67 promotion pipeline exist.
- Private audit evidence is not public benchmark or leaderboard evidence.
- No credentials, private logs, private workspace paths, real customer data, live execution, provider calls, or external actions are introduced.
