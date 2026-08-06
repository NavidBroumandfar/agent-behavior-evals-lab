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
