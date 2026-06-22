# Claim-Locked Public Release Bundle

M87 packages the M83-M86 local/open-weight benchmark release into a
public-safe, claim-locked handoff. The bundle records the exact wording the
project may use, the ranked rows it may show, the public artifacts that support
the release, and the unsupported claim families that must remain blocked.

Primary artifacts:

- `schemas/public_release_bundle.schema.json`
- `traces/external/public_release_bundle.example.json`
- `src/public_release_bundle.py`
- `tests/test_public_release_bundle.py`

## Release Scope

The bundle allows one release claim:

- public-safe local/open-weight ranking,
- `llama3.2:latest` and `mistral:latest`,
- `local_public_v1` extended split,
- two reviewed local Ollama ledgers,
- M83 report status `published_local_ranking`,
- M86 release label `public_safe_local_open_weight_ranking`.

The bundle does not add new model evidence and does not broaden the claim.

## Blocked Wording

The bundle carries M86 blockers forward into release wording. It blocks cloud
ranking, hosted-provider comparison, production-safety proof, third-party
model-output regeneration, private-audit proof, smoke/control ranking, deferred
`gemma4:latest` ranking, and raw-output publication.

Each blocked claim has a release instruction that starts with `Do not` and a
concrete unlock requirement.

## Validation

`python3 scripts/dev.py check` runs `src/public_release_bundle.py`. The
validator checks the bundle against the M86 checklist and the published local
report, verifies ranked rows, confirms public artifacts exist, scans selected
release-facing docs for unsupported positive claim phrasing, and rejects raw or
private source paths.

The validation is metadata-only. It does not run local models, call providers,
submit hosted jobs, inspect private evidence, read raw outputs, handle
credentials, or perform external actions.
