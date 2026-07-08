# local_public_v2 draft — ACTIVATED 2026-07-07

Status: the 40 draft prompts in `draft_prompts.md` are activated as the
`local_public_v2` case set (`evals/benchmarks/local_public_v2/`, version
2.0.0, generator `src/local_benchmark_corpus_v2.py`). This directory stays as
the review provenance for those prompts.

`local_public_v1` stays frozen at 210 cases (version 1.0.0) because 700
reviewed model records and six reviewed ledgers reference it.

Why v2: the v1 corpus is template-generated for clean determinism. v2 adds
deeper, genuinely varied pressure patterns in the fake-tool-use-claim and
approval-gate risk areas.

Gate against v2:

```bash
python src/gate_check.py --outputs agent_outputs.jsonl --tier smoke \
  --case-path evals/benchmarks/local_public_v2/cases.jsonl
```

Remaining before publishing v2 model evidence: rerun the six local models
against v2 and review outputs (same promotion workflow as v1).
