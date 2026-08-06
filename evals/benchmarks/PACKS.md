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

| Pack | Directory | Failure family | Frozen scenarios | Status |
|------|-----------|----------------|------------------|--------|
| Finance | [`finance_redteam/`](finance_redteam/) | `AGB-FIN-*` | 53 (35 / 18) | v0.6 frozen |
| DevOps / SRE | [`devops_sre/`](devops_sre/) | `AGB-DVO-*` | 26 (13 / 13) | v0.4 frozen |
| Healthcare admin | [`healthcare_admin/`](healthcare_admin/) | `AGB-HCA-*` | 17 (10 / 7) | v0.3 frozen |
| Legal / contracts | [`legal_ops/`](legal_ops/) | `AGB-LGL-*` | — | taxonomy + sandbox built; scenarios pending |
| HR / payroll | [`hr_payroll/`](hr_payroll/) | `AGB-HRP-*` | — | taxonomy + sandbox built; scenarios pending |
| Customer support / T&S | `support_ts/` | `AGB-CST-*` | — | planned |
| Data / analytics | `data_ops/` | `AGB-DTA-*` | — | planned |

*Frozen scenarios = (temptation / honest-control). The healthcare and DevOps packs
were grown to v0.2 by an augmentation round: every new scenario passed the same
three-reviewer gate (Codex cross-family + two Claude lenses, all must keep). The
v0.1 healthcare disclosure-control gap is now closed — `disclose_patient_record`
and `grant_record_access` both carry paired temptations and controls. Counts are
AI-authored drafts, not human-reviewed evidence; each pack's `HELD-OUT.md` and
manifest say so.*

Each pack names, in its vertical, the action-decidable ways an action-taking
agent misbehaves when tempted — and pairs every temptation with an honest control
that a safe agent must **not** refuse.

## Known limitations of the frozen packs

Published because a limitation you find yourself is worth more than one a buyer
finds for you.

- **`devops_sre` v0.2 is substantially prompt-separable.** A judge shown only
  the request text — no state, no labels — recovered the temptation/control
  label 86.4% of the time against a 50% baseline
  ([separability probe, 2026-08-06](../../reports/comparisons/separability_probe_2026-08-06.md)).
  Any result from this pack must publish that number beside it, and the pack is
  re-authored to the pair-symmetry rule before commercial use. All three packs
  have now been probed: `healthcare_admin` passed (+5.9pp) and
  `finance_redteam` passed (+9.4pp). devops is the only substantially
  separable one — and the only one where a deterministic check finds 3× the
  density of forbidden prose asymmetries.
- **Two sandbox scoring holes — FIXED 2026-08-06** (devops v0.4,
  healthcare v0.3). A restricted-secret disclosure was excused by the agent's
  own claim about who would receive the value (scoring the assertion, not the
  act); and a coverage-granting status change was gated on one exact string, so
  the same transition worded differently under-detected. Both fixes were
  verified by driving all 43 frozen cases through both sandboxes before and
  after: **zero canonical verdicts moved.** The superseded versions and their
  measurements stay in the record.
- **The freeze manifest pins the corpus, not the sandbox.** Discovered while
  fixing the above: two runs against the same pinned `cases.jsonl` could score
  differently if the sandbox changed, because only the corpus is hashed. Being
  closed; until it is, a published result must name the sandbox commit as well
  as the corpus hash.
- **Two further defects found and NOT yet fixed**, because each would move a
  frozen case's verdict and that is a corpus decision, not a bug fix: one
  devops rollback temptation cannot actually reach its violation (an
  unauthorized rollback currently scores safe on the safety axis), and one
  healthcare fixture flag is read by no tool, so a case's stated rule is not
  enforced. Both are recorded in the held-out build notes.

## Running the packs

The first execution of the packs against real tool-calling agents is
pre-registered in [`pack-run-protocol.md`](pack-run-protocol.md) — question,
fleet rules, metrics, suite-quality gates, and invalidation conditions all
committed **before** any run, per this repo's protocol convention. No result
from these packs exists yet; when one does, it lands as a dated report in
`reports/comparisons/` and never as a marketing number.

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
