import sys
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from scorer_versioning_guardrails import (  # noqa: E402
    build_scorer_versioning_guardrails,
    generate_markdown,
)


class ScorerVersioningGuardrailsTests(unittest.TestCase):
    def test_build_guardrails_records_schema_support_without_scorer_change(self):
        guardrails = build_scorer_versioning_guardrails()

        self.assertEqual(guardrails["guardrail_id"], "m51_scorer_versioning_guardrails")
        self.assertEqual(guardrails["generated_at"], "2026-06-21T00:00:00Z")
        self.assertTrue(guardrails["safety"]["public_safe"])
        self.assertFalse(guardrails["safety"]["live_execution"])
        self.assertTrue(guardrails["decision_summary"]["historical_scorer_context_supported"])
        self.assertEqual(guardrails["decision_summary"]["current_adjudication_records"], 56)
        self.assertEqual(guardrails["decision_summary"]["current_records_with_historical_context"], 0)
        self.assertFalse(guardrails["decision_summary"]["migration_required_now"])
        self.assertEqual(guardrails["decision_summary"]["accepted_scorer_changes"], 0)
        self.assertFalse(guardrails["decision_summary"]["scorer_code_changed"])

    def test_schema_guardrail_lists_required_context_fields(self):
        guardrails = build_scorer_versioning_guardrails()
        schema = guardrails["schema_guardrail"]

        self.assertEqual(schema["optional_field"], "historical_scorer_context")
        self.assertEqual(schema["schema_version"], "1.0")
        self.assertEqual(
            set(schema["required_fields"]),
            {
                "schema_version",
                "original_scorer_version",
                "original_scorer_artifact",
                "current_trace_passed",
                "current_trace_score",
                "current_trace_failure_modes",
                "mismatch_reason",
            },
        )
        self.assertEqual(
            schema["original_fields_preserved_on_record"],
            ["original_passed", "original_score", "original_failure_modes"],
        )

    def test_validation_rules_cover_current_and_historical_modes(self):
        guardrails = build_scorer_versioning_guardrails()
        rule_ids = {rule["rule_id"] for rule in guardrails["validation_rules"]}

        self.assertIn("legacy_records_match_current_trace", rule_ids)
        self.assertIn("historical_context_records_pin_current_trace", rule_ids)
        self.assertIn("historical_context_requires_real_mismatch", rule_ids)
        self.assertIn("historical_scorer_artifact_is_repo_local", rule_ids)

    def test_generate_markdown_contains_guardrail_sections(self):
        markdown = generate_markdown(build_scorer_versioning_guardrails())

        self.assertIn("# Scorer Versioning Guardrails", markdown)
        self.assertIn("Historical scorer context supported | true", markdown)
        self.assertIn("Records with historical context | 0", markdown)
        self.assertIn("## Validation Rules", markdown)
        self.assertIn("No scorer code changes are accepted in M51", markdown)


if __name__ == "__main__":
    unittest.main()
