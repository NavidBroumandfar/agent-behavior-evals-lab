import copy
import json
import sys
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from validate_benchmark_claim_charter import (  # noqa: E402
    BenchmarkClaimCharterValidationError,
    validate_charter,
)


CHARTER_PATH = REPO_ROOT / "benchmarks/evidence_class_charter.json"
SCHEMA_PATH = REPO_ROOT / "schemas/benchmark_claim_charter.schema.json"


def load_charter():
    return json.loads(CHARTER_PATH.read_text(encoding="utf-8"))


def write_charter(path, charter):
    path.write_text(json.dumps(charter, sort_keys=True, indent=2) + "\n", encoding="utf-8")


class BenchmarkClaimCharterValidationTests(unittest.TestCase):
    def validate_charter_object(self, charter):
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "evidence_class_charter.json"
            write_charter(path, charter)
            return validate_charter(path, SCHEMA_PATH)

    def assert_charter_error(self, charter, message):
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "evidence_class_charter.json"
            write_charter(path, charter)
            with self.assertRaisesRegex(BenchmarkClaimCharterValidationError, message):
                validate_charter(path, SCHEMA_PATH)

    def test_committed_benchmark_claim_charter_validates(self):
        summary = validate_charter(CHARTER_PATH, SCHEMA_PATH)

        self.assertEqual(summary["charter_path"], "benchmarks/evidence_class_charter.json")
        self.assertEqual(summary["schema_path"], "schemas/benchmark_claim_charter.schema.json")
        self.assertEqual(summary["charter_id"], "m54_local_benchmark_claim_charter")
        self.assertEqual(summary["evidence_class_count"], 7)
        self.assertEqual(
            summary["public_ranking_eligible_classes"],
            ["cloud_public_benchmark", "local_public_benchmark"],
        )
        self.assertEqual(summary["private_data_allowed_classes"], ["private_audit"])
        self.assertEqual(
            summary["credentials_required_allowed_classes"],
            ["cloud_public_benchmark", "private_audit"],
        )

    def test_rejects_missing_required_evidence_class(self):
        charter = load_charter()
        charter["evidence_classes"] = [
            item
            for item in charter["evidence_classes"]
            if item["evidence_class_id"] != "cloud_public_benchmark"
        ]

        self.assert_charter_error(charter, "missing required classes: cloud_public_benchmark")

    def test_rejects_private_audit_public_ranking(self):
        charter = load_charter()
        private_audit = next(
            item
            for item in charter["evidence_classes"]
            if item["evidence_class_id"] == "private_audit"
        )
        private_audit["public_ranking_eligible"] = True

        self.assert_charter_error(charter, "public_ranking_eligible")

    def test_rejects_local_benchmark_credentials_requirement(self):
        charter = load_charter()
        local_benchmark = next(
            item
            for item in charter["evidence_classes"]
            if item["evidence_class_id"] == "local_public_benchmark"
        )
        local_benchmark["credentials_required_allowed"] = True

        self.assert_charter_error(charter, "credentials_required_allowed must be false")

    def test_rejects_manual_sample_ranking_eligibility(self):
        charter = load_charter()
        manual_sample = next(
            item
            for item in charter["evidence_classes"]
            if item["evidence_class_id"] == "manual_public_sample"
        )
        manual_sample["public_ranking_eligible"] = True

        self.assert_charter_error(charter, "public_ranking_eligible is only allowed")

    def test_rejects_missing_source_path(self):
        charter = load_charter()
        charter["source_paths"] = ["docs/missing.md"]

        self.assert_charter_error(charter, "does not exist")

    def test_original_charter_object_is_not_mutated_by_helper_copy(self):
        charter = load_charter()
        copied = copy.deepcopy(charter)

        self.validate_charter_object(copied)

        self.assertEqual(copied, charter)
        self.assertEqual(charter, load_charter())


if __name__ == "__main__":
    unittest.main()
