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

from compare_scored_traces import ScoredTraceComparisonError, build_comparison, compare_scored_traces
from tests.test_validate_schemas import valid_trace_record


def trace_record(case_id, profile_name, passed=True, failure_modes=None, score=None):
    record = valid_trace_record()
    record["case_id"] = case_id
    record["profile_name"] = profile_name
    record["passed"] = passed
    record["score"] = 1.0 if score is None and passed else 0.0 if score is None else score
    record["failure_modes"] = [] if failure_modes is None else failure_modes
    return record


def write_jsonl(path, records):
    with path.open("w", encoding="utf-8") as output_file:
        for record in records:
            output_file.write(json.dumps(record, sort_keys=True, separators=(",", ":")))
            output_file.write("\n")


class CompareScoredTracesTests(unittest.TestCase):
    def test_build_comparison_detects_changed_new_and_resolved_failures(self):
        before = [
            trace_record("SAFE-001", "generic_assistant", passed=True),
            trace_record("SAFE-002", "generic_assistant", passed=False, failure_modes=["over_refusal"]),
            trace_record("SAFE-003", "generic_assistant", passed=True),
        ]
        after = [
            trace_record("SAFE-001", "generic_assistant", passed=False, failure_modes=["unsupported_claim"]),
            trace_record("SAFE-002", "generic_assistant", passed=True),
            trace_record("SAFE-004", "generic_assistant", passed=True),
        ]

        comparison = build_comparison(before, after)

        self.assertEqual(comparison["before_summary"]["failed"], 1)
        self.assertEqual(comparison["after_summary"]["failed"], 1)
        self.assertEqual(len(comparison["changed_records"]), 2)
        self.assertEqual(len(comparison["new_failures"]), 1)
        self.assertEqual(len(comparison["resolved_failures"]), 1)
        self.assertEqual(len(comparison["new_records"]), 1)
        self.assertEqual(len(comparison["removed_records"]), 1)

    def test_compare_scored_traces_writes_report(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            before_path = root / "before.jsonl"
            after_path = root / "after.jsonl"
            output_path = root / "comparison.md"
            write_jsonl(before_path, [trace_record("SAFE-001", "generic_assistant", passed=True)])
            write_jsonl(after_path, [trace_record("SAFE-001", "generic_assistant", passed=False, failure_modes=["unsupported_claim"])])

            summary = compare_scored_traces(before_path, after_path, output_path, "Temporary Comparison")

            self.assertEqual(summary["changed_records"], 1)
            self.assertTrue(output_path.exists())
            self.assertIn("Temporary Comparison", output_path.read_text(encoding="utf-8"))

    def test_duplicate_trace_keys_are_rejected(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            before_path = root / "before.jsonl"
            after_path = root / "after.jsonl"
            output_path = root / "comparison.md"
            duplicate = trace_record("SAFE-001", "generic_assistant", passed=True)
            write_jsonl(before_path, [duplicate, copy.deepcopy(duplicate)])
            write_jsonl(after_path, [trace_record("SAFE-001", "generic_assistant", passed=True)])

            with self.assertRaises(ScoredTraceComparisonError):
                compare_scored_traces(before_path, after_path, output_path, "Temporary Comparison")


if __name__ == "__main__":
    unittest.main()
