# Evidence Model

The project separates evidence classes so reports cannot overclaim.

## Main Evidence Classes

- Evaluator health: proves the local evaluator pipeline and gate work.
- Manual public sample: public-safe manually collected output; useful for
  workflow proof, not ranking by default.
- Local public benchmark: public-safe local/open-weight benchmark evidence.
- Cloud public benchmark: future public-safe hosted-provider benchmark evidence.
- Private audit: local-only private runtime evidence.
- Promoted public evidence: reviewed and redacted derivative evidence promoted
  from private or live sources.

## Public Ranking Rule

Public rankings require public-safe, ledger-backed evidence that satisfies the
ranking methodology. Private evidence and manual samples cannot enter public
rankings unless explicitly promoted into a public-safe evidence class.

## Private Evidence Rule

Private evidence may support private audit findings, but it must not support
public reproducibility or leaderboard claims unless redacted and promoted.

## Report Language

Reports should state:

- evidence class;
- source artifacts;
- sample size;
- known limitations;
- excluded evidence;
- claim boundaries.

Reports should not claim production compliance proof or broad model quality
without the required evidence.
