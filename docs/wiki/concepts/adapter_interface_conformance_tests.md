# Adapter Interface Conformance Tests

Adapter interface conformance tests prove that the M4 adapter boundary is enforceable, not just documented. After M4, the repository has a normalized adapter-output schema, a validator, an importer, a dry-run adapter contract path, and a provider-agnostic interface design. M5.1 adds tests around that boundary so future adapter work has executable expectations before any live collection is considered.

## Valid Fixture Validation

Valid fixture tests check that committed public-safe adapter-output records still satisfy the contract:

- `traces/external/adapter_outputs.example.jsonl`
- `traces/external/dry_run_adapter_outputs.jsonl`

They also check that `src/dry_run_adapter.py` can emit records into a temporary JSONL file and that those records validate successfully. The dry-run path is deterministic and local; it is a contract fixture producer, not a model adapter.

## Import Conformance

The importer test runs `src/import_adapter_outputs.py` through its reusable function with a temporary output path. This confirms that valid normalized adapter outputs can join to existing eval cases, use the existing scorer, and produce deterministic scored traces without writing test output to production trace paths.

This test does not change scoring logic. It verifies that the adapter boundary can feed the existing evaluator path.

## Invalid Contract Rejection

Invalid records must fail before they become scored traces. The tests create invalid JSONL files in temporary directories and assert that validation rejects records with missing required fields, unknown `source_type`, invalid UTC timestamp shape, empty `output_text`, unsafe provenance values, malformed `provenance_details`, invalid provenance-detail enum values, non-string provenance notes, private/sensitive blocked classification, and future live execution mode.

An unknown `case_id` is different: the record shape can validate, but import must reject it because the evaluator cannot connect it to an existing case. That keeps case ownership on the evaluator side and prevents orphaned adapter output from being scored.

## Why Invalid Examples Stay Out Of Traces

Invalid examples should not live under `traces/external/` because those paths are treated as public fixtures. Keeping invalid examples in temporary test files prevents the quality gate from confusing negative test data with production fixtures and avoids accidental import into `traces/scored/`.

This protects provenance and trace integrity. A scored trace should represent a validated input joined to a known eval case, not malformed adapter output.

## Future Adapter Protection

Future provider, local model, CLI agent, or OpenClaw adapters should first prove that their saved outputs conform to the same normalized record shape. The conformance tests make the required behavior clear:

- Preserve stable IDs and `case_id`.
- Emit supported `target_profile` and `source_type` values.
- Provide final text as `output_text`.
- Include public-safe provenance.
- Include valid `provenance_details` when origin, execution mode, data classification, or evidence limits need to be explicit.
- Reject live execution, external actions, and private data in committed deterministic fixtures.
- Reject future-only live execution and private/sensitive classification in current gated fixture validation.

The evaluator remains provider-agnostic because the tests target the normalized JSONL boundary, not provider-specific response objects.

## Still Not Live Execution

M5.1 does not add live provider APIs, SDKs, local model execution, live OpenClaw execution, browser/email tools, credentials, network calls, private runtime integration, or real adapters. It only strengthens local deterministic tests for saved adapter-output fixtures and the no-network dry-run contract path.
