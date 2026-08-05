# What this pack publishes, and what it deliberately withholds

This directory publishes the **method, the taxonomy, and (after a scored run) the
results** of a healthcare-administration agent red-team. It does **not** publish
the scenarios.

## Withheld (gitignored, local only)

| File | What it is |
|---|---|
| `cases.jsonl` | the temptation + honest-control scenarios |
| `healthcare_sandbox_tools.py` | the mock healthcare-admin sandbox the scenarios run in |
| `manifest.json` | the sha256 freeze record over the scenarios |
| `BUILD-NOTES.md` | the provenance log, which quotes scenarios directly |

## Why

**A published eval set is a burned eval set.** These scenarios only measure
anything while the model under test has not seen them. Anything committed to a
public repository is scraped into the next training run, after which a model can
pass by recall rather than by behaving safely. This is a measurement-integrity
reason before it is a commercial one — the same reason held-out test sets are not
shipped with the training data. It is also the boundary this repository already
committed to (see [`../../../PUBLIC_REPO_BOUNDARY.md`](../../../PUBLIC_REPO_BOUNDARY.md)).

Every patient, provider, and identifier in the withheld files is **synthetic** —
no real PHI exists here — but the scenarios are still withheld for the
measurement-integrity reason above.

## What IS published, and why that is the useful half

- **[`METHODOLOGY.md`](METHODOLOGY.md)** — the charter: how scenarios are built,
  vetted by two blind reviewers, and frozen before anything is scored.
- **[`healthcare_failure_taxonomy.md`](healthcare_failure_taxonomy.md)** — the
  named, action-decidable ways a healthcare-admin agent fails. The vocabulary is
  more useful shared than hoarded.
- **[`../PACK-SPEC.md`](../PACK-SPEC.md)** and the shared factory
  (`src/pack_conformance.py`, `src/vertical_pack_scorer.py`,
  `src/pack_archetype_check.py`) — the conformance rules and scorer, with tests.
- **`reports/`** (once a scored run exists) — the actual measurements, including
  the ones that go badly and the claims that get withdrawn.
