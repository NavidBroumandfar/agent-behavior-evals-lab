# Fixture Manifest

The fixture manifest is a deterministic index of controlled external fixture families. It lives at `traces/external/fixture_manifest.json` and records which source fixtures exist, which scripts own their validation or import path, which scored traces they generate, which reports include them, and what limitations apply.

It is an audit artifact, not a scoring artifact. It does not duplicate scored results and it does not replace the existing validators, importers, replay scripts, or reports.

## Why It Exists

M4 added normalized adapter-output validation, import, dry-run contract output, and external fixture comparison. M5.1 made adapter-interface conformance executable. M5.2 added provenance details for adapter-output records.

M5.3 adds a source index because the fixture ecosystem now spans several controlled paths:

- Manual saved outputs.
- Sanitized OpenClaw-style manual samples.
- Saved transcript replay.
- Sanitized OpenClaw-style saved transcript pilot fixtures.
- Normalized adapter-output fixtures.
- Dry-run adapter-output fixtures.

The manifest makes those paths easy to audit without reading every script first.

## Source, Trace, Report

A source fixture is public-safe input under `traces/external/`. It contains saved text, saved transcript turns, sanitized saved transcript pilot turns, normalized adapter-output records, or deterministic dry-run adapter-output records.

A generated scored trace is evaluator output under `traces/scored/`. It is created after the source fixture is validated or imported, joined to eval cases, scored by the existing scorer, and written in trace JSONL form.

A report is Markdown under `reports/` or `reports/comparisons/`. Reports summarize existing scored traces; they do not collect new target outputs.

The manifest links these layers so a reader can move from a fixture source to the generated trace and report without guessing which script owns the path.

## Auditability

Each manifest entry records:

- Fixture identity and source path.
- Source kind and source type.
- Provenance class and data classification.
- Owning validation/import scripts.
- Generated scored trace path and expected counts.
- Included report paths.
- Whether the fixture is in the local quality gate.
- Explicit safety assertions.
- Limitations and public-safe notes.

`src/validate_fixture_manifest.py` checks that referenced files exist, JSONL counts match, quality-gate flags are booleans, and committed fixtures do not claim live execution, external actions, private data, or credentials.

## Not Live Execution

The manifest does not imply live provider, local model, or OpenClaw execution. It indexes saved deterministic artifacts only.

It does not add provider APIs, SDKs, local model runtimes, browser or email tools, external actions, credentials, network calls, private runtime integration, real adapters, or scoring changes.

## Future Adapter Work

Future adapter work can add a new controlled fixture family to the manifest after it has a clear source path, validation/import path, generated scored trace, quality-gate status, provenance class, and limitations.

That keeps the evaluator provider-agnostic: new target-side collection mechanisms can be documented as fixture sources without changing the scorer or making the public quality gate execute live systems.
