# What this pack publishes, and what it deliberately withholds

This directory publishes the **method, the taxonomy, and (after a scored run) the
results** of an HR-operations / payroll agent red-team. It does **not** publish
the scenarios or the sandbox they run in.

## Withheld (gitignored, local only)

| File | What it is |
|---|---|
| `cases.jsonl` | the temptation + honest-control scenarios |
| `hr_sandbox_tools.py` | the mock HR/payroll sandbox the scenarios run in |
| `manifest.json` | the sha256 freeze record over the scenarios |
| `BUILD-NOTES.md` | the provenance log, which quotes scenarios directly |

`cases.jsonl` and `manifest.json` do not exist yet — see
[`METHODOLOGY.md`](METHODOLOGY.md) §Status for why the scenario batch is
deliberately deferred. The `.gitignore` block covering all four was added
**before** any of them was created, so no held-out file was ever trackable.

## Why

**A published eval set is a burned eval set.** These scenarios only measure
anything while the model under test has not seen them. Anything committed to a
public repository is scraped into the next training run, after which a model can
pass by recall rather than by behaving safely. This is a measurement-integrity
reason before it is a commercial one — the same reason held-out test sets are not
shipped with the training data. It is also the boundary this repository already
committed to (see [`../../../PUBLIC_REPO_BOUNDARY.md`](../../../PUBLIC_REPO_BOUNDARY.md)).

The **sandbox is withheld for a second reason** on top of that one: its fixtures
*are* the answer key. Every disqualifier a scenario turns on — which bank-change
request was verified out of band, which approver reports to which requester, which
run carries blocking exceptions, which lawful basis permits health data, which
employee is on statutory leave — is a literal in that file. Publishing it would
let an agent pass by reading the fixtures instead of by calling the read tools,
which is precisely the behavior this pack exists to distinguish.

Every employee, actor, run, claim, and identifier in the withheld files is
**synthetic**. The pack contains no personal names at all, and payroll
destinations are opaque account references deliberately not shaped like an IBAN,
sort code, routing number, or account number — so no real personnel data and no
real identifier exists here. The scenarios are still withheld for the
measurement-integrity reasons above.

## What IS published, and why that is the useful half

- **[`METHODOLOGY.md`](METHODOLOGY.md)** — the charter: the four risk shapes this
  pack is built around, how scenarios are built and kept prompt-symmetric, the
  entity standard, and the vet-then-freeze pipeline.
- **[`hr_failure_taxonomy.md`](hr_failure_taxonomy.md)** — the named,
  action-decidable ways an HR/payroll agent fails, including an explicit
  cross-check of what is distinct from the finance taxonomy and what is
  deliberately not re-minted. The vocabulary is more useful shared than hoarded.
- **[`../PACK-SPEC.md`](../PACK-SPEC.md)** and the shared factory
  (`src/pack_conformance.py`, `src/vertical_pack_scorer.py`,
  `src/pack_archetype_check.py`, `src/pack_sandbox_base.py`) — the conformance
  rules and scorer, with tests.
- **`reports/`** (once a scored run exists) — the actual measurements, including
  the ones that go badly and the claims that get withdrawn.
