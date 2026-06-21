# Retention Consent Access Controls

M69 adds operational metadata controls for private runtime evidence and private
audit mode. The committed contract is public-safe fake metadata only; it does
not collect, read, delete, export, or inspect private evidence.

## Metadata Contract

`schemas/retention_consent_access.schema.json` validates:

- retention policy metadata,
- consent and authorization checklist requirements,
- access-control notes for local private stores,
- deletion and export boundaries,
- aggregate-only public summary output defaults,
- quality-gate exclusions,
- no-overclaim safety assertions,
- per-record fake metadata for retention class, fake age, authorization status,
  access boundary, and deletion/export boundary.

The fixture at `traces/external/retention_consent_access_metadata.example.json`
links to the M66 private evidence vault and M68 private audit report metadata.

## Retention And Age Reporting

The validator calculates fake evidence age from committed metadata timestamps
and an `evidence_age_as_of` boundary timestamp. The committed summary reports
aggregate age signals only, including oldest, newest, and average fake evidence
age in days.

Retention classes stay metadata-only:

- `delete_after_review`
- `retain_local_until_manually_deleted`

## Consent And Authorization

Each fake record must carry a public-safe consent or authorization state that
matches the source vault metadata. If authorization is still required, the
committed fixture records that requirement without embedding authorization
proof, private subject details, customer data, or private reviewer evidence.

## Access, Deletion, And Export Boundary

M69 checks that the private evidence and private report roots match M66/M68 and
remain ignored by Git. Delete targets are limited to ignored private roots, but
the deterministic gate does not execute deletion.

Private artifact export is disabled by default. The committed export is an
aggregate public-safe summary under `reports/comparisons/`; it does not contain
raw private evidence, private artifact paths, credentials, real customer data,
or per-record private values.

## Quality-Gate Boundary

`python3 scripts/dev.py check` validates M69 using fake metadata only. It does
not ingest private evidence, read raw private logs, handle credentials or
secrets, call providers, run models, execute Hermes, OpenClaw, production
systems, browser/email/network/shell actions, external actions, deletion
actions, export actions, or gated LLM review.

M69 does not create public leaderboard evidence, production-safety proof,
third-party reproducibility evidence, or private-audit overclaims.
