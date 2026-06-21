# Redaction And Promotion Pipeline

The redaction and promotion pipeline converts selected private-evidence records
into public-safe derivative fixtures. It is the bridge between private audit
evidence and promoted public evidence, but it does not make private evidence
public by default.

M67 uses fake M66 private-vault metadata and a synthetic promoted output. The
deterministic gate validates the promotion contract without reading private
artifacts.

## Required Inputs

The M67 pipeline validates three public-safe input groups:

- a promotion candidate manifest,
- diffable redaction notes,
- promoted public-safe adapter-output records.

The source private artifact remains under `private_evidence/` and is referenced
only as local-only metadata. The validator does not open or read that path.

## Redaction Checklist

Every promotion candidate must declare that:

- the source record exists in the private vault manifest,
- the original artifact remains local-only,
- redaction notes exist,
- reviewer signoff exists,
- public-safety assertions exist,
- the promoted output validates as public-safe,
- no raw private values, hidden prompts, private paths, or credentials are retained.

## Diffable Redaction Notes

`schemas/redaction_note.schema.json` defines field-level redaction actions. Each
action names a field path, sensitive class, redaction method, replacement label,
and rationale. Raw source values are never retained in the note.

This keeps review diffable without putting private values in Git.

## Promoted Output Boundary

Promoted outputs are normalized adapter-output records. They must validate as
public-safe fixtures and include redaction metadata linking the derivative to
its candidate and redaction note.

The committed promoted output must not include secrets, account data, private
paths, hidden prompts, raw runtime logs, real customer data, live execution, or
external actions.

Promoted private evidence is not public ranking evidence by default. It can only
support claims allowed by its declared evidence class.

## Quality-Gate Boundary

`python3 scripts/dev.py check` validates the schema, redaction notes, promoted
output, report summaries, and safety assertions. It does not ingest private
evidence, read raw private logs, handle credentials or encryption keys, call
providers, execute agents, use browser/email/network tools, or perform external
actions.
