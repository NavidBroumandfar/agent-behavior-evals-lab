# Fixture Manifest Validation Tests

Fixture manifest validation tests prove that the fixture source index cannot drift into misleading claims about controlled sources, generated scored traces, reports, quality-gate inclusion, or public-safe provenance.

The tests live in `tests/test_fixture_manifest_validation.py`. They use temporary manifests and temporary fixture files for invalid cases, so malformed examples do not enter `traces/external/` or any production trace/report path.

## Fixture Records Vs Fixture Index

Fixture record validation checks the contents of a specific fixture format. For example, normalized adapter-output validation checks adapter-output JSONL records and their `provenance` fields.

Fixture manifest validation checks the index around those fixture families. It verifies that source paths, scored trace paths, report paths, expected counts, quality-gate flags, and safety assertions are coherent.

These are separate checks. A fixture record can be valid while the manifest entry for that fixture is wrong or misleading.

## Invalid Classes Blocked

The tests cover top-level manifest failures such as malformed JSON, non-object manifests, missing required fields, invalid `fixtures` shape, and empty fixture lists.

They also cover fixture-entry failures such as missing identifiers, source metadata, ownership fields, scored trace paths, report paths, quality-gate flags, expected counts, limitations, missing referenced files, and source count mismatches.

Public-boundary tests reject manifest entries that claim live execution, external actions, private data, credential requirements, or private/sensitive data classification.

## Why It Matters

The manifest is an audit index. If it claims a fixture is public-safe, quality-gated, or represented in a report, that claim must be mechanically checked before the repository presents it as part of the deterministic fixture ecosystem.

This prevents accidental provenance inflation, stale path references, incorrect counts, and report/source mismatches from making the public portfolio harder to audit.

## Still Not Live Execution

M5.4 does not add provider APIs, provider SDKs, local model execution, live OpenClaw execution, browser/email tools, external actions, credentials, network calls, private runtime integration, real adapters, or scoring changes.

It only adds local unit tests for the manifest validator and keeps invalid examples in temporary test files.
