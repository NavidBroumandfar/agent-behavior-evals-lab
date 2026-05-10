# External Fixture Comparison

An external fixture comparison summarizes already-scored traces that came from controlled saved-output inputs. It compares fixture families, not live systems.

M4.3 adds `src/compare_external_fixtures.py` and `reports/comparisons/external_fixture_comparison_report.md`. The script reads scored trace JSONL files that already exist in `traces/scored/`, validates them against the current trace schema, groups them by fixture source, and writes a deterministic Markdown report.

## Compared Sources

The report currently compares:

- Manual output fixture: `traces/scored/manual_output_eval.jsonl`
- Sanitized OpenClaw-style manual fixture: `traces/scored/openclaw_manual_eval.jsonl`
- Saved transcript replay fixture: `traces/scored/saved_transcript_replay_eval.jsonl`
- Normalized adapter-output import fixture: `traces/scored/adapter_output_fixture_import.jsonl`

These inputs are scored traces, not raw adapter records. The comparison script does not import adapter outputs, replay transcripts, or evaluate manual outputs itself; the quality gate regenerates those deterministic dependencies before it generates the comparison report.

## Saved Outputs, Not Live Systems

External fixture comparison is a reporting layer over public-safe saved outputs. It does not call provider APIs, run local models, execute OpenClaw, use browser or email tools, perform external actions, use credentials, or inspect private runtime state.

The OpenClaw-style source group is a sanitized fictional fixture. It is useful for exercising evaluator reporting across a system-under-test label, but it is not evidence of real OpenClaw execution.

## No Scoring Change

M4.3 does not change scoring logic. Each input trace already contains `passed`, `score`, `failure_modes`, `severity`, `category`, and `rationale` from the existing evaluator path that produced it.

The comparison report aggregates those existing fields. It can show pass/fail rates, average scores, failure mode distribution, severity distribution, category distribution, and notable failed records without changing the scorer or trace semantics.

## Why It Helps

Fixture comparison makes it easier to analyze behavior across source types:

- Manual outputs show the smallest saved-output path.
- Sanitized OpenClaw-style samples show public-safe system-under-test examples without live execution.
- Saved transcript replay shows selected assistant turns from static conversations.
- Normalized adapter-output import shows the M4 adapter-output contract feeding the existing evaluator trace shape.

Because the report uses fixed inputs, fixed timestamps, stable sorting, and deterministic formatting, repeated quality-gate runs should not dirty generated artifacts.

## Preparing M4.4

M4.4 can add an adapter dry-run contract test. The comparison report gives that work a stable downstream consumer: future dry-run records can be validated, imported, scored through existing logic, and compared as another saved fixture family without creating a real adapter or adding live execution.

Run the report from the repository root:

```bash
python3 src/compare_external_fixtures.py
```
