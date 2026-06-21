# Private Evidence Vault

The private evidence vault is a local-only boundary for private runtime
evidence. It exists so the lab can eventually support private audit workflows
without mixing private artifacts into public fixtures, public reports, or public
rankings.

M66 adds the vault contract, not private evidence ingestion. The committed
manifest uses fake public-safe metadata only.

## Local Storage Boundary

Private evidence belongs under ignored local paths by default:

- `private_evidence/` for raw private runtime artifacts, redaction notes, and local-only metadata.
- `reports/private/` for private audit reports generated from actual private evidence.

The deterministic quality gate checks that these roots are ignored by Git. It
does not read files from those roots.

## Manifest Contract

`schemas/private_evidence_manifest.schema.json` defines the public-safe metadata
required for private evidence records:

- local-only artifact path,
- evidence class,
- retention class,
- access boundary,
- consent or authorization requirement,
- redaction metadata,
- private-audit report label,
- safety assertions that no raw private content appears in the manifest.

The committed example at
`traces/external/private_evidence_vault_manifest.example.json` contains fake
metadata records only.

## Promotion Boundary

M66 does not promote private records. It validates that promotion would require
explicit redaction metadata, reviewer signoff, and public-safety assertions. The
current promotion preflight refuses M66 records because the redaction and
promotion pipeline is planned for M67.

Private evidence cannot support public rankings unless a reviewed derivative is
redacted, validated, and explicitly promoted into a public-safe fixture.

## Report Boundary

Reports generated from actual private evidence must be marked
`private_audit_report` and remain local-only under `reports/private/` by default.

The committed M66 report at
`reports/comparisons/private_evidence_vault_summary.md` is not a private audit
report. It is a public-safe boundary summary generated from fake metadata.

## Quality-Gate Boundary

`python3 scripts/dev.py check` validates the schema, fake metadata, ignored path
controls, promotion blocking, and summary reports. It does not ingest private
evidence, read raw private logs, handle credentials or encryption keys, call
providers, execute agents, use browser/email/network tools, or perform external
actions.
