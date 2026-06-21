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

from local_benchmark_corpus import (  # noqa: E402
    DEFAULT_CASE_PATH,
    DEFAULT_MANIFEST_PATH,
    build_cases,
    build_manifest,
    case_jsonl,
    sha256_text,
)
from validate_local_benchmark_corpus import (  # noqa: E402
    DEFAULT_CASE_SCHEMA_PATH,
    DEFAULT_MANIFEST_SCHEMA_PATH,
    LocalBenchmarkCorpusValidationError,
    validate_corpus,
)


def load_cases():
    return [
        json.loads(line)
        for line in DEFAULT_CASE_PATH.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def load_manifest():
    return json.loads(DEFAULT_MANIFEST_PATH.read_text(encoding="utf-8"))


class LocalBenchmarkCorpusTests(unittest.TestCase):
    def validate_case_objects(self, cases, manifest_updates=None):
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_root = Path(temp_dir)
            case_path = temp_root / "cases.jsonl"
            case_text = case_jsonl(cases)
            case_path.write_text(case_text, encoding="utf-8")

            for source_path in load_manifest()["source_paths"]:
                path = temp_root / source_path
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text("fixture source\n", encoding="utf-8")

            manifest = build_manifest(cases, DEFAULT_CASE_PATH, sha256_text(case_text))
            manifest["case_path"] = "cases.jsonl"
            if manifest_updates:
                manifest_updates(manifest)

            manifest_path = temp_root / "manifest.json"
            manifest_path.write_text(json.dumps(manifest, sort_keys=True, indent=2) + "\n", encoding="utf-8")
            return validate_corpus(
                manifest_path,
                DEFAULT_MANIFEST_SCHEMA_PATH,
                DEFAULT_CASE_SCHEMA_PATH,
                repo_root=temp_root,
            )

    def assert_corpus_error(self, cases, message, manifest_updates=None):
        with self.assertRaisesRegex(LocalBenchmarkCorpusValidationError, message):
            self.validate_case_objects(cases, manifest_updates)

    def test_committed_local_benchmark_corpus_validates(self):
        summary = validate_corpus(DEFAULT_MANIFEST_PATH, DEFAULT_MANIFEST_SCHEMA_PATH, DEFAULT_CASE_SCHEMA_PATH)

        self.assertEqual(summary["manifest_path"], "evals/benchmarks/local_public_v1/manifest.json")
        self.assertEqual(summary["case_path"], "evals/benchmarks/local_public_v1/cases.jsonl")
        self.assertEqual(summary["case_set_id"], "local_public_v1")
        self.assertEqual(summary["version"], "1.0.0")
        self.assertEqual(summary["case_count"], 210)
        self.assertEqual(summary["split_counts"], {"extended": 210, "smoke": 21, "standard": 70})
        self.assertEqual(
            summary["risk_area_counts"],
            {
                "approval_gate": 30,
                "privacy": 30,
                "production_change": 30,
                "refusal_boundary": 30,
                "safe_task": 30,
                "tool_use_claim": 30,
                "uncertainty": 30,
            },
        )

    def test_generator_builds_expected_case_count(self):
        cases = build_cases()

        self.assertEqual(len(cases), 210)
        self.assertEqual(cases[0]["case_id"], "LPB-SAFE-001")
        self.assertEqual(cases[-1]["case_id"], "LPB-PRODCHANGE-030")
        self.assertEqual(cases[0]["benchmark_splits"], ["smoke", "standard", "extended"])
        self.assertEqual(cases[10]["benchmark_splits"], ["extended"])

    def test_rejects_duplicate_case_id(self):
        cases = load_cases()
        cases[1]["case_id"] = cases[0]["case_id"]

        self.assert_corpus_error(cases, "duplicate case_id")

    def test_rejects_missing_case(self):
        cases = load_cases()[:-1]

        self.assert_corpus_error(cases, "must contain 210 cases")

    def test_rejects_wrong_split_membership(self):
        cases = load_cases()
        cases[0]["benchmark_splits"] = ["extended"]

        self.assert_corpus_error(cases, "benchmark_splits")

    def test_rejects_manifest_coverage_mismatch(self):
        cases = load_cases()

        def update_manifest(manifest):
            manifest["coverage"]["by_risk_area"]["privacy"] = 1

        self.assert_corpus_error(cases, "coverage.by_risk_area", update_manifest)

    def test_rejects_case_hash_mismatch(self):
        cases = load_cases()

        def update_manifest(manifest):
            manifest["case_file_sha256"] = "0" * 64

        self.assert_corpus_error(cases, "case_file_sha256", update_manifest)

    def test_rejects_missing_source_path(self):
        cases = load_cases()

        def update_manifest(manifest):
            manifest["source_paths"] = ["docs/missing-source.md"]

        self.assert_corpus_error(cases, "does not exist", update_manifest)

    def test_rejects_unsafe_manifest_assertion(self):
        cases = load_cases()

        def update_manifest(manifest):
            manifest["safety_assertions"]["live_execution"] = True

        self.assert_corpus_error(cases, "live_execution", update_manifest)

    def test_original_committed_artifacts_are_not_mutated_by_helper_copy(self):
        cases = load_cases()
        copied_cases = copy.deepcopy(cases)

        self.validate_case_objects(copied_cases)

        self.assertEqual(cases, load_cases())
        self.assertEqual(load_manifest(), json.loads(DEFAULT_MANIFEST_PATH.read_text(encoding="utf-8")))


if __name__ == "__main__":
    unittest.main()
