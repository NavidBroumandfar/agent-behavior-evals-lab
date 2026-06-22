# Public Release Checklist

Use this checklist before publishing public benchmark claims, release bundles,
or open-source release notes.

## Required Checks

- `python3 scripts/dev.py test`
- `python3 scripts/dev.py check`
- `python3 scripts/dev.py lint` when dev tooling is installed

## Claim Review

- Report declares its evidence class.
- Public rankings use only eligible public benchmark evidence.
- Private-only evidence is excluded from public rankings.
- Manual samples are excluded from rankings unless the methodology explicitly
  allows them.
- Limitations are present in the report.
- No production compliance proof is claimed.
- No cloud ranking is claimed without cloud evidence.

## Public-Safe Review

- No credentials, tokens, cookies, or private URLs.
- No raw private traces, private memory, hidden prompts, or customer logs.
- No private workspace paths.
- No unredacted screenshots or transcripts.
- No customer-specific findings.

## Release Bundle

- Cases, manifest, prompt template, scorer artifact, outputs, traces, reports,
  and methodology have stable hashes where applicable.
- Reproduction instructions are included.
- Exclusions are explicit.
