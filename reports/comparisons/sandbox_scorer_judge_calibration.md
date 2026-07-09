# Keyword Scorer vs LLM Judge: Calibration Study

Where the deterministic keyword scorer and an LLM judge disagree on the
same reviewed model outputs. Disagreement labels are from the scorer's
point of view: a *false alarm* means the scorer failed a record the judge
passed; a *miss* means the scorer passed a record the judge failed.

- Scored runs: 1
- Judge model(s): gemma4:latest (a local judge is itself imperfect; disagreement localizes review-worthy records, it does not adjudicate them)
- Judged records: 24
- Agreement: 24 (100.0%)
- Scorer false alarms (scorer FAIL, judge PASS): 0
- Scorer misses (scorer PASS, judge FAIL): 0

> **Read this as a sanity pass, not a validation.** These 24 records are
> hand-authored, unambiguous exemplars (12 designed-pass / 12 designed-fail);
> 100% agreement means the scorer and judge do not *conflict* on clear-cut cases,
> not that the scorer is validated. Scorer credibility comes from divergence on
> real, messy outputs — see the 700-record model study
> ([`scorer_judge_calibration.md`](scorer_judge_calibration.md)) and the
> real-agent fleet calibration
> ([`sandbox_fleet_scorer_judge_calibration.md`](sandbox_fleet_scorer_judge_calibration.md)),
> where the baseline is the structural tool-event verifier and disagreement is
> both expected and informative.

## Per run

| Run | Judged | Agreement | Scorer false alarms | Scorer misses |
| --- | --- | --- | --- | --- |
| `sandbox_agent_benchmark_eval` | 24 | 100.0% | 0 | 0 |

## Disagreements by category

| Category | Disagreements |
| --- | --- |

_Judge outputs are opt-in, local-only artifacts (`*.judge.local.jsonl`,
git-ignored). This report aggregates them deterministically._
