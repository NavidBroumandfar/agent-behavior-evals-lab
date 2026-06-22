# Claim Review And Release Checklist

M86 adds a public-safe claim-review checklist for the current local/open-weight
benchmark release. The checklist is a metadata gate: it validates what the
project may say about the published report and what it must not say.

Primary artifacts:

- `schemas/claim_review_checklist.schema.json`
- `traces/external/claim_review_checklist.example.json`
- `src/claim_review_checklist.py`
- `tests/test_claim_review_checklist.py`

## Allowed Claim

The current release may describe one scoped claim:

- a public-safe local/open-weight ranking for `llama3.2:latest` and
  `mistral:latest`,
- over the `local_public_v1` extended split,
- backed by two eligible reviewed local Ollama ledgers,
- with `reports/comparisons/local_open_weight_benchmark_v1.json` in
  `published_local_ranking` state.

## Blocked Claims

The checklist blocks claims that would overstate the evidence:

- cloud-model ranking,
- hosted-provider comparison,
- production-safety proof,
- third-party output regeneration,
- private-audit proof,
- smoke/control ranking from `qwen3.5:2b-q4_K_M`,
- current ranking claims for deferred `gemma4:latest`,
- raw-output publication.

Every blocked claim has a concrete blocker ID and an unlock requirement. This
keeps release wording from using vague missing-context language when the real
answer is that the evidence class does not support the claim.

## Quality Gate

`python3 scripts/dev.py check` runs `src/claim_review_checklist.py`. The
validator cross-checks the checklist against the evidence charter, local report,
real-model proof runbook, runtime stability profile, and hosted-provider
metadata. It does not run local models, call providers, read raw outputs, read
private evidence, handle credentials, or perform external actions.
