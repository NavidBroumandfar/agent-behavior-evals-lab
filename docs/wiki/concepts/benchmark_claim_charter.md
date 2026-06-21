# Benchmark Claim Charter

M54 defines the evidence classes and claim boundaries for the zero-cost local benchmark path.

Primary artifacts:

- `benchmarks/evidence_class_charter.json`
- `schemas/benchmark_claim_charter.schema.json`
- `src/validate_benchmark_claim_charter.py`

The charter exists to keep the lab's evidence claims precise. It separates evaluator-health evidence, local/open-weight benchmark evidence, manual public samples, cloud benchmark evidence, private audit evidence, promoted public evidence, and unsupported claims.

## Evidence Classes

- `evaluator_health`: proves the local evaluator pipeline, reports, and quality gate work on committed artifacts. It does not support model rankings or production-policy proof.
- `local_public_benchmark`: public-safe local or open-weight model evidence, such as an Ollama or local OpenAI-compatible run. It can support local/open-weight rankings when the run protocol is fixed.
- `manual_public_sample`: public-safe saved output collected manually. It can prove the workflow functions, but it is excluded from rankings by default.
- `cloud_public_benchmark`: public-safe hosted-provider evidence. It can support cloud-model rankings only after actual provider output and metadata exist.
- `private_audit`: local-only private runtime evidence for internal audit. It is not committed and cannot support public rankings.
- `promoted_public_evidence`: reviewed and redacted derivative evidence that can be committed only after public-safe promotion.
- `unsupported_claim`: a claim the current evidence cannot support.

## Ranking Rules

Public rankings require public evidence. Local rankings must be labeled local, and cloud rankings require cloud-provider evidence. Private audit evidence is excluded from public rankings unless it is redacted, reviewed, promoted, and then satisfies the relevant public evidence class.

Manual samples remain useful as workflow proof, but they are not enough for a leaderboard unless a later methodology explicitly promotes them into a benchmark evidence class.

## Boundary

The charter is a local committed policy artifact. Its validator checks schema shape, evidence-class completeness, ranking boundaries, private-evidence restrictions, source paths, and safety assertions.

It does not run Ollama, local models, provider APIs, Hermes, OpenClaw, CLI agents, browser/email tools, shell commands, file mutations, network collectors, private logs, credentials, gated LLM review, or external actions.
