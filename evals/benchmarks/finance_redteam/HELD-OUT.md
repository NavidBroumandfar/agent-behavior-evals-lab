# What this pack publishes, and what it deliberately withholds

This directory publishes the **method, the instrument, and the results** of a
finance agent red-team. It does **not** publish the scenarios themselves.

## Withheld

| File | What it is |
|---|---|
| `cases.jsonl` | the 53 scenarios (35 temptation / 18 honest control) |
| `finance_sandbox_tools.py` | the mock finance sandbox the scenarios run in |
| `manifest.json` | the sha256 freeze record over the scenarios |
| `BUILD-NOTES.md` | the provenance log, which quotes scenarios directly |

## Why

**A published eval set is a burned eval set.** These scenarios only measure
anything while the model under test has not seen them. Anything committed to a
public repository is scraped into the next training run, after which a model can
pass by recall rather than by behaving safely. The file could be deleted; the
training data could not be un-learned.

This is a measurement-integrity reason before it is a commercial one. It is the
same reason held-out test sets are not shipped with the training data.

It is also the boundary this repository already committed to: see
[`PUBLIC_REPO_BOUNDARY.md`](../../../PUBLIC_REPO_BOUNDARY.md), which places
"proprietary case packs and sector-specific rubrics" out of public scope.

## What IS published, and why that is the useful half

- **`METHODOLOGY.md`** — the charter: how scenarios are built, vetted by two blind
  reviewers, and frozen before anything is scored.
- **`finance_failure_taxonomy.md`** — the named, action-decidable ways a finance
  agent fails. The vocabulary is more useful shared than hoarded.
- **`A4-run-protocol.md`** — the pre-registered run protocol, committed before any
  scored run existed.
- **`reports/`** — the actual measurements, including the ones that went badly and
  the claims that were withdrawn.
- **`src/finance_redteam_scorer.py`**, **`finance_redteam_runner.py`**,
  **`finance_sandbox_mcp_server.py`** — the grading machine and the harness, in full.

You can read exactly how the grading works, reproduce the scoring logic, run the
harness against your own cases, and check whether the reported numbers follow from
the stated method. What you cannot do is read the exam questions — which is the
point of an exam.

## Consequence, stated plainly

**The published numbers are not independently reproducible from this repository.**
Reproducing them requires the withheld corpus. That is a real limitation and it is
the deliberate cost of keeping the instrument alive. Reports state their corpus
version and sha256 so a holder of the corpus can verify them exactly.
