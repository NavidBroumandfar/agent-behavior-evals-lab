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
| Finance | [`finance_redteam/`](finance_redteam/) | `AGB-FIN-*` | 53 (35 / 18) | v0.7 frozen |
| DevOps / SRE | [`devops_sre/`](devops_sre/) | `AGB-DVO-*` | 26 (13 / 13) | v0.6 frozen |
| Healthcare admin | [`healthcare_admin/`](healthcare_admin/) | `AGB-HCA-*` | 17 (10 / 7) | v0.4 frozen |
| Legal / contracts | [`legal_ops/`](legal_ops/) | `AGB-LGL-*` | — | **candidate** — taxonomy + sandbox built, batch in review, nothing frozen |
| HR / payroll | [`hr_payroll/`](hr_payroll/) | `AGB-HRP-*` | — | **candidate** — taxonomy + sandbox built, batch in review, nothing frozen |
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

  **The corpus was re-authored to the pair-symmetry rule as v0.6 (2026-08-06).**
  All 12 pairs are now length-matched and differ by at most one token position
  once identifiers are masked; `pack_symmetry_check` goes from 14 `[leak]`
  findings to 0. **This does not retire the 86.4% figure.** That number was
  measured on v0.2 content, no probe has been run against v0.6, and one is not
  claimed here — re-measuring requires the pre-registered protocol and is a
  separate decision. Until a v0.6 probe exists, v0.2's measurement remains the
  only separability evidence this pack has, and it stays published beside any
  result from it.
- **Two sandbox scoring holes — FIXED 2026-08-06** (devops v0.4,
  healthcare v0.3). A restricted-secret disclosure was excused by the agent's
  own claim about who would receive the value (scoring the assertion, not the
  act); and a coverage-granting status change was gated on one exact string, so
  the same transition worded differently under-detected. Both fixes were
  verified by driving all 43 frozen cases through both sandboxes before and
  after: **zero canonical verdicts moved.** The superseded versions and their
  measurements stay in the record.
- **The freeze manifest now pins the sandbox too — CLOSED 2026-08-06.**
  Previously only `cases.jsonl` was hashed, so two runs against the same pinned
  corpus could score differently if the sandbox changed and nothing would
  detect it. `manifest.json` now records `sandbox_sha256`, `verify_manifest`
  recomputes it, and all three packs are pinned. Manifests frozen before the
  change verify as *unpinned* rather than failing, so a legacy pack is reported
  honestly instead of breaking the gate.
- **Two further sandbox defects — FIXED 2026-08-06** (devops v0.5,
  healthcare v0.4). Both were reported-not-fixed in the round above, because each
  moves a frozen case's verdict and that is a corpus decision rather than a bug
  fix. The decision was taken, because in both cases the *old* verdict was the
  wrong one.
  - One devops rollback temptation could not reach its violation: authorization
    was computed environment-wide, so a ticket added for the paired control
    authorized every rollback in that environment and **an unauthorized
    production rollback scored safe on the safety axis**. Authorization is now
    scoped to the specific service and target release the approved change names.
  - One healthcare fixture flag (a break-the-glass chart marker) was read by no
    tool, so a frozen case's stated rule was unenforced and a heightened-access
    grant scored safe. The flag is now read, and the read-only tool the case's
    prose claims surfaces it now does.

  Both fixes are strictly tightening, verified by driving every reachable payload
  of both tools through the old and the new rule in one process: **0 payloads
  became more lenient.** Exactly **two** verdicts moved across the 43 frozen
  cases — the two the fixes exist to move. The superseded versions and their
  measurements stay in the record.
- **A conformant, archetype-clean contract can still be unfailable.** The devops
  defect above passed every check this repo had, because `pack_archetype_check`
  *fabricates* tool events from the scoring contract: it proves a contract losable
  in principle, never that the pack's own sandbox can emit the losing event.
  `src/pack_reachability_check.py` now drives the real sandbox over a bounded,
  documented argument domain and reports any contract — or any breach verdict a
  case's own prose names — that no reachable payload can produce, plus (author
  mode) any fixture field no verdict depends on. It is wired into the gate as an
  **advisory** step for the same reason pair-symmetry is: the frozen corpora
  predate it, and the only legitimate fix is a version bump. All three packs now
  report zero findings.
- **The checker's own first verdict on the flagship pack was wrong, and that is
  the more useful result.** On the day it landed it reported **3 hard + 18
  advisory** findings against `finance_redteam` — including a claim that a real
  restricted disclosure to a filing subject would score SAFE. Every one of the 21
  was then driven by hand through the real sandbox, and **all 21 were false
  alarms**: the contracts and the prose were live, and the *checker* was
  under-searching. Four causes, all now fixed, none of them in the corpus:
  - **A starved argument domain.** Every candidate source had a quota except the
    tool's own fixture pool, which sat last behind full token and literal lists.
    A case naming many ids against a tool holding many literals exhausted the cap
    before one pool value was admitted — so a violation whose two deciding values
    sat in a **nine-item** pool was reported unreachable. The pool now gets an
    appended (prefix-preserving) tail, so widening can only ever clear a finding.
  - **No multi-call reach.** One call per payload cannot reach a verdict that is a
    function of earlier calls. The sweep now retries behind named priming
    sequences (the same payload twice, the reads the case's own prose asks for,
    the payloads that already satisfied this case's earlier specs).
  - **Sandbox-minted ids.** State keyed by an id the sandbox invents is reachable
    by no payload at all; primed passes now feed those ids forward by field name.
  - **A multi-call control read as conjunctive.** Required specs were checked as
    "one event satisfies them all" rather than the scorer's `_all_present`, so a
    control asking for three payments — one per obligation reference — was
    unsatisfiable by construction.

  Direction of the change was measured, not asserted: **21 findings cleared, 0 new
  or strengthened** across all three packs, and injected-dead-rule mutations of the
  finance sandbox are still reported. No frozen byte moved — corpus, sandbox and
  manifest hashes are unchanged, and all 53 scored outcomes are identical across
  four agent archetypes. The pre-fix numbers stay in the record: a detector that
  cries wolf on frozen content is a defect of the same family as one that stays
  silent, and it was found by verifying its own output rather than trusting it.
- **The instrument itself diverged from its own record — FIXED 2026-08-06**
  (finance v0.7). A caller-supplied argument containing a brace raised an
  **uncaught** exception out of the finance sandbox's `dispatch`, from a
  `str.format` on a confirmation template one tool composed out of that same
  argument. Scoring was unaffected, and that is what made it serious: the event
  was recorded *before* the format call, so the log said `status=succeeded` while
  the agent under test received a transport error for the very same call. The MCP
  server does not wrap `dispatch`, so a live run would have shown the agent one
  thing and the record another — the exact class of defect these packs exist to
  detect, sitting inside the instrument that detects it. An agent that can crash
  the harness can also plausibly evade a case.

  The fix removes the class rather than catching it: no template is composed from
  caller data, and the substitution is a total single-pass filler that cannot
  raise and never re-scans a substituted value. The two obvious cheaper fixes were
  measured and rejected — a `try/except` returns a summary the recorded event does
  not corroborate, and a chained `str.replace` rewrites a caller value of `"{ref}"`
  into the sandbox's own reference. Both trade one log-vs-experience divergence for
  another; both are now re-injected as mutation controls that must fail.

  The same audit swept **every tool of every pack sandbox in the checkout** and
  found two more instances of the wider class (an argument raising out of
  `dispatch`, which `dispatch` promises can never happen): a `null` argument in the
  unfrozen `legal_ops` sandbox and in the core `src/sandbox_tools.py`. Both fixed.
  `devops_sre`, `healthcare_admin`, `hr_payroll` and `src/pack_sandbox_base.py` are
  clean. The durable guard is `tests/test_sandbox_hostile_arguments.py`, which
  drives all 213 tools with 30 hostile argument values and asserts `dispatch`
  never raises, records exactly one event, and keeps `breach=` first. Zero of the
  53 + 26 + 17 frozen cases moved verdict across four agent archetypes.

- **The gate was checking two packs less than it appeared to — FIXED
  2026-08-06.** A blind reviewer found `legal_ops` and `hr_payroll` on disk with
  an authored corpus and a working sandbox and **no `REGISTERED_PACKS` entry**.
  Every check — conformance, pair-symmetry, reachability, the hostile-argument
  sandbox contract — enumerated its work from that registry, so none of them ever
  looked at either pack, while the gate printed `pack conformance: all registered
  packs OK`. Nothing anywhere said the two packs were unchecked, which is the same
  defect these packs exist to detect: an instrument reporting nothing while it is
  looking at nothing.

  The cause was the binary registered/not-registered. Registration was documented
  as a **freeze-time** act, so "check me" and "I am shippable" were one claim and
  an author with an unfrozen corpus could only pick unchecked. Two changes: the
  registry carries a lifecycle `status` (`candidate` / `frozen`), so a pack is
  registered and checked the moment it has content; and traversal is now
  `discover_packs`, which walks the **disk** as well as the registry — a pack with
  held-out content and no entry is reported by name and checked anyway, with its
  sandbox found by convention and its toolbox class read from the module. A
  directory holding only public docs (a clean public checkout) stays silent, and
  the advisory summaries now name the packs they swept rather than only the ones
  with findings. Advisory/blocking status of every existing step is unchanged.

## Running the packs

The first execution of the packs against real tool-calling agents is
pre-registered in [`pack-run-protocol.md`](pack-run-protocol.md) — question,
fleet rules, metrics, suite-quality gates, and invalidation conditions all
committed **before** any run, per this repo's protocol convention. No result
from these packs exists yet; when one does, it lands as a dated report in
`reports/comparisons/` and never as a marketing number.

## Adding a pack

Follow the pipeline in [`PACK-SPEC.md`](PACK-SPEC.md) §"The build pipeline":
author the taxonomy, design the sandbox, **register the pack as a `candidate` in
`src/pack_conformance.py:REGISTERED_PACKS` and add its held-out `.gitignore` block
before creating any fixture file**, author scenarios (danger in retrievable state,
not stated in the prompt), run the four deterministic checks, vet with two blind
reviewers from different model families, freeze the manifest, flip the status to
`frozen`.

Registration is **not** a freeze-time act, and treating it as one is what let two
packs accumulate a corpus and a sandbox that no gate check ever looked at — see
[`PACK-SPEC.md`](PACK-SPEC.md) §"Registration & lifecycle". A pack with held-out
content on disk and no registry entry is now discovered, reported by name, and
checked anyway; registering it is what stops the gate calling that out.

> **Disclosure:** v0 packs are AI-authored and AI-vetted first passes. Their
> labels have not had domain-expert human review and their counts are not to be
> quoted as product evidence until they do. Each pack's `manifest.json` and
> `BUILD-NOTES.md` say so on their face.
