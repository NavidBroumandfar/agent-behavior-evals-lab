# Milestone 86 - Claim Review And Release Checklist

Status: Complete / public-safe claim gate published
Date: 2026-06-22

## Summary

M86 adds a final public-safe claim-review checklist for the current
local/open-weight benchmark release. The checklist allows the scoped
local/open-weight ranking claim and blocks unsupported claims with concrete
blocker IDs and unlock requirements.

This milestone does not run a local model, inspect raw outputs, submit hosted
provider jobs, read private evidence, use credentials, or add live execution to
the deterministic quality gate.

## Completed

- Added `schemas/claim_review_checklist.schema.json`.
- Added `traces/external/claim_review_checklist.example.json`.
- Added `src/claim_review_checklist.py`.
- Added `tests/test_claim_review_checklist.py`.
- Wired claim-review checklist validation into `scripts/check_all.py`.
- Added wiki and schema-coverage documentation.

## Allowed Release Claim

The release may describe a public-safe local/open-weight ranking for:

| Rankable model | Runtime | Split | Sample | Claim scope |
| --- | --- | --- | ---: | --- |
| `llama3.2:latest` | `ollama` | `extended` | 210 | current local/open-weight ranking |
| `mistral:latest` | `ollama` | `extended` | 210 | current local/open-weight ranking |

The claim is bounded to the committed `local_public_v1` extended split, the M59
methodology, the M79 and M82 reviewed ledgers, and the M83 report status
`published_local_ranking`.

## Blocked Claims

M86 blocks the following unsupported claims:

- cloud-model ranking,
- hosted-provider comparison,
- production-safety proof,
- third-party model-output regeneration,
- private-audit proof,
- ranking from smoke/control evidence,
- ranking from deferred `gemma4:latest` evidence,
- publication of raw local outputs.

Each blocked claim has a concrete blocker and an unlock requirement in
`traces/external/claim_review_checklist.example.json`.

## Boundary

M86 does not broaden the published benchmark. It does not make
`gemma4:latest`, `gemma4:31b-cloud`, or `qwen3.5:2b-q4_K_M` ranking-eligible.
It keeps hosted-provider evidence separate and keeps raw/local-only artifacts
ignored and uncommitted.

## Validation

From the repository root:

```bash
python3 src/claim_review_checklist.py
python3 scripts/dev.py check
```
