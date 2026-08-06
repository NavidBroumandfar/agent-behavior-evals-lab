# What this pack publishes, and what it deliberately withholds

This directory publishes the **method, the taxonomy, and (after a scored run) the
results** of a legal-operations agent red-team. It does **not** publish the
scenarios or the sandbox they run in.

## Withheld (gitignored, local only)

| File | What it is |
|---|---|
| `cases.jsonl` | the temptation + honest-control scenarios (**candidate batch in review; nothing frozen**) |
| `legal_sandbox_tools.py` | the mock in-house-legal sandbox the scenarios run in |
| `manifest.json` | the sha256 freeze record over the scenarios |
| `BUILD-NOTES.md` | the provenance log, which quotes scenarios directly |

The four-line `.gitignore` block for these paths was added **before** any of
them was created, per [`../PACKS.md`](../PACKS.md) §"Adding a pack" — so no
held-out file in this pack has ever been trackable.

## Why

**A published eval set is a burned eval set.** These scenarios only measure
anything while the model under test has not seen them. Anything committed to a
public repository is scraped into the next training run, after which a model can
pass by recall rather than by behaving safely. This is a measurement-integrity
reason before it is a commercial one — the same reason held-out test sets are not
shipped with the training data. It is also the boundary this repository already
committed to (see [`../../../PUBLIC_REPO_BOUNDARY.md`](../../../PUBLIC_REPO_BOUNDARY.md)).

The **sandbox** is withheld for a second, pack-specific reason: in this vertical
the sandbox *is* half the answer key. Every disqualifier lives in retrievable
fixture state — which document is privileged, which delegation is suspended,
which deadline is statutory, which matter record sits inside a preservation
scope. Publishing the fixtures would let a model learn the state table and score
without ever reading it, which is precisely the failure the pair-symmetry rule
exists to prevent.

Every matter, contract, document, firm, counterparty, hold, and handle in the
withheld files is **synthetic** — this pack contains no coined proper nouns at
all, no real party, firm, docket, case number, or privileged material — but the
files are still withheld for the measurement-integrity reasons above.

## What IS published, and why that is the useful half

- **[`METHODOLOGY.md`](METHODOLOGY.md)** — the binding charter: the schema, the
  discipline rules, the pair-symmetry rule in its legal-ops form (with a worked
  symmetric pair and a worked leaking pair), the entity standard as applied to
  law-firm and counterparty naming, and the extension instructions.
- **[`legal_failure_taxonomy.md`](legal_failure_taxonomy.md)** — the 13 named,
  action-decidable ways a legal-ops agent fails, each with the tool-log signature
  that decides it and an explicit note on why it is not a relabel of a
  finance/devops/healthcare mode. The vocabulary is more useful shared than
  hoarded.
- **[`../PACK-SPEC.md`](../PACK-SPEC.md)** and the shared factory
  (`src/pack_conformance.py`, `src/vertical_pack_scorer.py`,
  `src/pack_archetype_check.py`, `src/pack_sandbox_base.py`) — the conformance
  rules, the event contract, and the scorer, with tests.
- **`reports/`** (once a scored run exists) — the actual measurements, including
  the ones that go badly and the claims that get withdrawn.

## Current state

There is **no scenario library yet**, on purpose. The taxonomy, the sandbox, and
this charter exist; authoring waits on the pair-symmetry checker so this pack is
built symmetric from the first case rather than retrofitted like `devops_sre`
v0.2. Nothing here has been scored, no count is quotable, and the labels have had
no review by a qualified lawyer.
