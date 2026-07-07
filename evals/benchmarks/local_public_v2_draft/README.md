# local_public_v2 draft — ACTIVATED 2026-07-07

Status: the 40 draft prompts in `draft_prompts.md` are activated as the
`local_public_v2` case set (`evals/benchmarks/local_public_v2/`, version
2.0.0, generator `src/local_benchmark_corpus_v2.py`). This directory stays as
the review provenance for those prompts.

`local_public_v1` stays frozen at 210 cases (version 1.0.0) because 700
reviewed model records and six reviewed ledgers reference it.

Why v2: the v1 corpus is template-generated (6 base scenarios x 5 suffix
variants per risk area). That gives clean determinism but low scenario
diversity, and the suffix pattern is learnable. v2 focuses on the two
categories this project differentiates on — fake tool-use claims and approval
gates — with genuinely varied pressure patterns.

Gate against v2:

```bash
python src/gate_check.py --outputs agent_outputs.jsonl --tier smoke \
  --case-path evals/benchmarks/local_public_v2/cases.jsonl
```

Remaining before publishing v2 model evidence: rerun the six local models
against v2 and review outputs (same promotion workflow as v1).
