import json
import sys
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from local_ranking_methodology import (  # noqa: E402
    DEFAULT_EXAMPLE_INPUT_PATH,
    DEFAULT_EXAMPLE_REPORT_PATH,
    DEFAULT_EXAMPLE_SNAPSHOT_PATH,
    DEFAULT_METHODOLOGY_PATH,
    compute_example_results,
    generate_methodology_artifacts,
)
from validate_local_ranking_methodology import (  # noqa: E402
    DEFAULT_SCHEMA_PATH,
    LocalRankingMethodologyValidationError,
    validate_local_ranking_methodology,
)


def load_json(path):
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path, value):
    path.write_text(json.dumps(value, sort_keys=True, indent=2) + "\n", encoding="utf-8")


class LocalRankingMethodologyTests(unittest.TestCase):
    def assert_methodology_error(self, methodology, message):
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "methodology.json"
            write_json(path, methodology)
            with self.assertRaisesRegex(LocalRankingMethodologyValidationError, message):
                validate_local_ranking_methodology(
                    path,
                    DEFAULT_SCHEMA_PATH,
                    DEFAULT_EXAMPLE_INPUT_PATH,
                    DEFAULT_EXAMPLE_SNAPSHOT_PATH,
                )

    def assert_input_error(self, example_input, message):
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "input.json"
            write_json(path, example_input)
            with self.assertRaisesRegex(LocalRankingMethodologyValidationError, message):
                validate_local_ranking_methodology(
                    DEFAULT_METHODOLOGY_PATH,
                    DEFAULT_SCHEMA_PATH,
                    path,
                    DEFAULT_EXAMPLE_SNAPSHOT_PATH,
                )

    def assert_snapshot_error(self, snapshot, message):
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "snapshot.json"
            write_json(path, snapshot)
            with self.assertRaisesRegex(LocalRankingMethodologyValidationError, message):
                validate_local_ranking_methodology(
                    DEFAULT_METHODOLOGY_PATH,
                    DEFAULT_SCHEMA_PATH,
                    DEFAULT_EXAMPLE_INPUT_PATH,
                    path,
                )

    def test_committed_local_ranking_methodology_validates(self):
        summary = validate_local_ranking_methodology()

        self.assertEqual(summary["methodology_path"], "benchmarks/local_ranking_methodology.json")
        self.assertEqual(summary["schema_path"], "schemas/local_ranking_methodology.schema.json")
        self.assertEqual(summary["example_input_path"], "traces/external/local_ranking_methodology_inputs.example.json")
        self.assertEqual(summary["example_snapshot_path"], "reports/comparisons/local_ranking_methodology_example.json")
        self.assertEqual(summary["methodology_id"], "local_ranking_methodology_v1")
        self.assertEqual(summary["metric_count"], 6)
        self.assertEqual(summary["example_run_count"], 2)
        self.assertFalse(summary["ranking_claim_allowed"])

    def test_generator_can_write_public_safe_example_artifacts_to_temp_paths(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            summary = generate_methodology_artifacts(
                methodology_path=root / "methodology.json",
                example_input_path=root / "inputs.json",
                example_snapshot_path=root / "snapshot.json",
                example_report_path=root / "report.md",
            )

            self.assertEqual(summary["methodology_id"], "local_ranking_methodology_v1")
            self.assertEqual(summary["example_runs"], 2)
            self.assertEqual(summary["example_cases_per_run"], 21)
            self.assertFalse(summary["ranking_claim_allowed"])
            self.assertTrue((root / "methodology.json").exists())
            self.assertTrue((root / "inputs.json").exists())
            self.assertTrue((root / "snapshot.json").exists())
            self.assertTrue((root / "report.md").exists())

    def test_committed_artifacts_exist(self):
        for path in [
            DEFAULT_METHODOLOGY_PATH,
            DEFAULT_EXAMPLE_INPUT_PATH,
            DEFAULT_EXAMPLE_SNAPSHOT_PATH,
            DEFAULT_EXAMPLE_REPORT_PATH,
        ]:
            self.assertTrue(path.exists(), path)

    def test_computed_results_are_deterministic_and_example_only(self):
        methodology = load_json(DEFAULT_METHODOLOGY_PATH)
        example_input = load_json(DEFAULT_EXAMPLE_INPUT_PATH)

        first = compute_example_results(methodology, example_input)
        second = compute_example_results(methodology, example_input)

        self.assertEqual(first, second)
        self.assertEqual(first[0]["model"], "fake-local-model-alpha")
        self.assertEqual(first[0]["example_rank"], 1)
        self.assertFalse(first[0]["public_ranking_eligible"])
        self.assertIn("Synthetic methodology example", first[0]["exclusion_reasons"][0])

    def test_rejects_private_audit_evidence(self):
        example_input = load_json(DEFAULT_EXAMPLE_INPUT_PATH)
        example_input["runs"][0]["evidence_class"] = "private_audit"

        self.assert_input_error(example_input, "private_audit cannot be ranked")

    def test_rejects_partial_run_example(self):
        example_input = load_json(DEFAULT_EXAMPLE_INPUT_PATH)
        example_input["runs"][0]["run_status"] = "partial"

        self.assert_input_error(example_input, "partial runs are exclusions")

    def test_rejects_unresolved_review(self):
        example_input = load_json(DEFAULT_EXAMPLE_INPUT_PATH)
        example_input["runs"][0]["case_results"][0]["review_status"] = "needs_discussion"

        self.assert_input_error(example_input, "unresolved review is not allowed")

    def test_rejects_changed_severity_weights(self):
        methodology = load_json(DEFAULT_METHODOLOGY_PATH)
        methodology["severity_weights"]["high"] = 9.0

        self.assert_methodology_error(methodology, "severity_weights")

    def test_rejects_publishable_example_claim(self):
        snapshot = load_json(DEFAULT_EXAMPLE_SNAPSHOT_PATH)
        snapshot["ranking_claim_allowed"] = True

        self.assert_snapshot_error(snapshot, "ranking_claim_allowed")


if __name__ == "__main__":
    unittest.main()
