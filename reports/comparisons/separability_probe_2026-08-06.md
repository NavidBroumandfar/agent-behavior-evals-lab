# Prompt-only separability probe — partial run, 2026-08-06

**Protocol:** [`evals/benchmarks/separability-probe-protocol.md`](../../evals/benchmarks/separability-probe-protocol.md),
committed before this run. **Self-audit of our own instrument.** Aggregates
only; per-case results name held-out scenarios and stay local.

## What was measured

Can a judge that sees **only the request text** — no sandbox state, no tool
list, no labels, no scoring contract, one case per context, shuffled — recover
the hidden temptation/honest-control label?

If it can, the pack partly measures prose rather than behavior: an agent could
score well by reading tone and never checking state. That would undercut the
governing claim of this repo.

## Result

| Pack | Cases scored | Separability | Majority baseline | Delta | Pre-registered band |
|---|---|---|---|---|---|
| `devops_sre` v0.2 | 22 | **86.4%** (19/22) | 50.0% | **+36.4pp** | **> +30pp — substantially prose-separable** |
| `healthcare_admin` v0.2 | 17 | 64.7% (11/17) | 58.8% | +5.9pp | ≤ +10pp — label not carried by prompts |

Zero parse errors. Judge: Codex CLI (`gpt-5.6-sol`, GPT family) — not the family
that authored the packs, per the protocol's no-self-family rule. Shuffle seed
fixed at 20260806, so the presentation order is reproducible.

## Reading, per the rule fixed in advance

**`devops_sre` v0.2 lands in the worst band.** The pre-registered consequence
applies without amendment: any future run against this pack must publish this
number beside its results, and the pack is re-authored to the pair-symmetry
rule (`PACK-SPEC.md`) before it is used in a commercial engagement. The pack is
**not** edited in place — it stays frozen, with this measurement attached to it.

**`healthcare_admin` v0.2 passes cleanly.** Its prompts do not carry the label
at better than baseline plus 10 points. Worth stating because it cuts against
expectation: the healthcare pack's *candidate* batch was rejected the same day
for exactly this defect, while its frozen content does not show it.

## The confound, stated plainly

Temptations describe riskier actions than controls **by design** — that is the
domain, not a leak. So separability over-states the defect by an unknown
margin, and no part of this number should be read as "86% of the devops pack is
broken." What it does establish is that a prose-only judge does far better than
chance on that pack, which is enough to require the caveat above.

The protocol's sharper per-pair sortability metric, which partly controls for
this by comparing each temptation against its own same-tool control, was **not
computed in this run**. It is the first thing to add.

## Deviations from the pre-registered protocol

Disclosed rather than quietly absorbed:

1. **One judge family, not the specified two or more.** The protocol requires
   judges spanning ≥2 families; this run used a single GPT-family judge because
   the multi-family gateway is unavailable. This is therefore a **partial
   execution**, and the numbers are provisional until a second family confirms
   them. A single judge's idiosyncrasy is not separated from the signal here.
2. **Per-pair sortability not computed** (see above).
3. **`finance_redteam` v0.6 not probed** — the largest pack (53 cases) is still
   outstanding.

No threshold was moved, and the bands were fixed before any data existed. The
result fell where it fell.

## Independent corroboration, by a different method

Later the same day, and without access to this probe or its numbers, a blind
reviewer examining a separate scenario batch reported that the frozen
`devops_sre` **controls state their legitimizing fact in prose** — approval
asserted in the control, silent in the paired temptation — naming three frozen
pairs where this holds.

That is a *mechanism* for what this probe measured as a *rate*. Two methods —
one statistical and blind to the corpus internals, one structural and blind to
the statistics — converged on the same conclusion about the same pack. The
agreement raises confidence that the 86.4% is a genuine property of the content
rather than an artifact of one judge or one prompt framing.

It also sharpens the fix: the defect is concentrated in how *controls* are
written, not in the temptations.

## What this does not license

- It does not rank the packs against each other; different verticals, different n.
- It does not measure agent behavior at all — no agent was run.
- Small n (22 and 17). Intervals are wide; a two-case swing moves the devops
  figure by ~9pp.
- One judge, one prompt framing, one day.

## Next

1. Re-run with a second model family and compute per-pair sortability.
2. Probe `finance_redteam` v0.6.
3. Re-author the flagged `devops_sre` pairs to the pair-symmetry rule as v0.3;
   keep v0.2 and this measurement in the record.

---

## A cheap deterministic proxy — and a pre-registered prediction

After this probe, the pair-symmetry rule was implemented as a deterministic,
offline checker (`src/pack_symmetry_check.py`, no model calls). Pointed at the
three frozen corpora it reports "leak"-severity findings — a legitimizing
assertion present only in a control, or a hedge present only in a temptation:

| Pack | Leaks | Cases | Leaks per case | Probe separability |
|---|---|---|---|---|
| `devops_sre` | 14 | 26 | **0.54** | 86.4% (+36.4pp) |
| `finance_redteam` | 14 | 53 | 0.26 | **not yet run** |
| `healthcare_admin` | 3 | 17 | 0.18 | 64.7% (+5.9pp) |

On the two packs where both instruments ran, **they rank the packs the same
way**, and the gap is large in both: the pack with 3× the leak density is the
pack the judge separated far better. One free deterministic pass appears to
predict what an LLM probe measures.

Two independent runs is not a validation — it is a hypothesis with n=2. So it is
worth stating as a **falsifiable prediction, recorded before the measurement
exists**:

> `finance_redteam` v0.6 sits between the other two on leak density (0.26).
> If leak density tracks separability, its probe result should land **between**
> healthcare's +5.9pp and devops's +36.4pp — roughly +10pp to +30pp over its own
> majority baseline.
>
> **If finance lands outside that interval, the proxy claim is wrong** and the
> deterministic checker must not be described as predicting separability. It
> would remain useful as a rule-compliance check; it would not be a substitute
> for the probe.

The finance probe is the next thing to run. Whichever way it falls gets
published here, under this prediction.

---

## The prediction was falsified — result, 2026-08-06

`finance_redteam` v0.6, same protocol, same judge family, same fixed seed:

| Pack | Cases | Separability | Baseline | Delta | Protocol band |
|---|---|---|---|---|---|
| `finance_redteam` v0.6 | 53 | 75.5% (40/53) | 66.0% | **+9.4pp** | ≤ +10pp — **passes** |

**+9.4pp falls outside the +10pp–+30pp interval I predicted.** Narrowly — by
0.6pp — but the rule was written before the data and it does not get relaxed
now. Per that rule: **the proxy claim as I stated it is wrong.** The
deterministic checker must not be described as predicting a separability
*magnitude*.

Two things are true and the order matters:

1. **The quantitative prediction failed.** I said finance would land between
   +10pp and +30pp. It did not.
2. **The rank ordering held, 3 for 3.** Leak density ranks the packs
   devops (0.54) > finance (0.26) > healthcare (0.18). Separability ranks them
   devops (+36.4pp) > finance (+9.4pp) > healthcare (+5.9pp). Same order.

Retreating to claim 2 because claim 1 failed is exactly the move that makes
predictions worthless, so: **the interval prediction is recorded as wrong.**
The surviving rank-order relationship is a *weaker, separate* hypothesis, now
at n=3 with perfect rank agreement and no interval attached. It is worth more
testing and worth nothing as a marketing sentence.

What the checker is, then: a **rule-compliance detector** — it finds the specific
prose asymmetries `PACK-SPEC` forbids, cheaply and deterministically, and it
correctly identified devops as the worst offender. It is **not** a substitute
for the probe, and no number from it should be presented as a predicted
separability.

**Good news for the pack, separately:** finance v0.6 passes the protocol's own
band. Two of three frozen packs now pass; devops v0.2 remains the single
substantially-separable one, which is also the pack with 3× the leak density.

Same deviations still apply: one judge family, per-pair sortability not
computed. All three packs have now been probed.

---

## The fix was measured, and it worked — `devops_sre` v0.6, 2026-08-06

The 86.4% was measured on v0.2. That corpus has since been re-authored to the
pair-symmetry rule (`pack_symmetry_check` findings: 14 `[leak]` → 0). Re-probed
at the new pin (`corpus_sha256=1369d2c1…`, verified before the run), same judge,
same prompt, same shuffle seed 20260806 — the instrument held constant:

| `devops_sre` | Cases | Separability | Baseline | Delta | Band |
|---|---|---|---|---|---|
| **v0.2** (before) | 22 | 86.4% | 50.0% | **+36.4pp** | worst |
| **v0.6** (after) | 26 | 57.7% | 50.0% | **+7.7pp** | **passes** |

**A 28.7-point reduction, from the worst pre-registered band into the passing
one.** The pack now sits alongside healthcare (+5.9pp) and finance (+9.4pp)
rather than far outside them.

### Per-pair sortability — the sharper metric, computed this time

The protocol asked for it and the first run did not produce it. It compares each
temptation against **its own same-tool control**, which controls for prompt
topic in a way aggregate accuracy cannot:

- **2 of 12 pairs (16.7%)** — judge rated the temptation more suspicious than
  its own control.
- **8 of 12 tied** — identical suspicion for both halves. This is what symmetry
  looks like from the outside.
- **2 of 12 inverted** — the *control* read as more suspicious. Noise, and the
  expected shape when pairs are genuinely indistinguishable.

A pack where the judge can only sort 2 pairs in 12, and ties 8, is not handing
the answer to a prose-reader.

### What this does not establish

- **Still one judge family.** The multi-family gateway remains unavailable, so
  this repeats the disclosed deviation. Judge idiosyncrasy is not separated from
  signal. Both numbers come from the same judge, same day, same prompt, same
  seed, which controls the comparison well but does not make it multi-family.
- **Not a like-for-like case set.** v0.2 had 22 cases; v0.6 has 26 — the 22 were
  re-authored and 4 pair-symmetric cases were added. The question answered is
  "is the pack better now", not "is each case better".
- **The by-design floor still applies.** Temptations describe riskier actions
  than controls, so some separability is irreducible. +7.7pp is plausibly at or
  near that floor rather than proof of zero leakage.
- **Small n.** 26 cases; a two-case swing moves this ~8pp.
- **This measures test material, not agents.** No agent has been run against any
  pack.

### The honest ledger on this instrument

Two claims were made and tested today. The **quantitative proxy prediction
failed** (finance landed 0.6pp outside its predicted interval; recorded above,
not retracted). The **fix hypothesis held**: re-authoring to the rule that a
deterministic checker enforces moved the measured number by 28.7 points, in the
predicted direction, on a pre-registered instrument. One for two, both published.
