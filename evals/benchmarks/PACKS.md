# Vertical red-team packs — registry

*The packs this lab ships, and what each one publishes vs. holds out. Every pack
conforms to [`PACK-SPEC.md`](PACK-SPEC.md) and is scored on the recorded tool
log, never the wording.*

## What is public vs. held out

For **every** pack, the split is the same:

- **Published (the method):** `METHODOLOGY.md`, `HELD-OUT.md`, the
  `*_failure_taxonomy.md` vocabulary. Plus the shared factory: `PACK-SPEC.md`,
  `src/pack_conformance.py`, `src/vertical_pack_scorer.py`, and their tests.
- **Held out (the moat):** the scenario library (`cases.jsonl`), the mock sandbox
  (`*_sandbox_tools.py`), the freeze record (`manifest.json`), and the provenance
  log (`BUILD-NOTES.md`). A published eval set is a burned eval set — see any
  pack's `HELD-OUT.md`.

## Registry

| Pack | Directory | Failure family | Status |
|------|-----------|----------------|--------|
| Finance | [`finance_redteam/`](finance_redteam/) | `AGB-FIN-*` | v0.6 frozen |
| Healthcare admin | `healthcare_admin/` | `AGB-HCA-*` | v0 (in progress) |
| DevOps / SRE | `devops_sre/` | `AGB-DVO-*` | v0 (in progress) |
| Legal / contracts | `legal_ops/` | `AGB-LGL-*` | planned |
| HR / payroll | `hr_payroll/` | `AGB-HRP-*` | planned |
| Customer support / T&S | `support_ts/` | `AGB-CST-*` | planned |
| Data / analytics | `data_ops/` | `AGB-DTA-*` | planned |

Each pack names, in its vertical, the action-decidable ways an action-taking
agent misbehaves when tempted — and pairs every temptation with an honest control
that a safe agent must **not** refuse.

## Adding a pack

Follow the pipeline in [`PACK-SPEC.md`](PACK-SPEC.md) §"The build pipeline":
author the taxonomy, design the sandbox, author scenarios (danger in retrievable
state, not stated in the prompt), run `pack_conformance.py`, vet with two blind
reviewers from different model families, freeze the manifest. Register the pack in
`src/pack_conformance.py:REGISTERED_PACKS` and add its held-out `.gitignore` block
**before** creating any fixture file.

> **Disclosure:** v0 packs are AI-authored and AI-vetted first passes. Their
> labels have not had domain-expert human review and their counts are not to be
> quoted as product evidence until they do. Each pack's `manifest.json` and
> `BUILD-NOTES.md` say so on their face.
