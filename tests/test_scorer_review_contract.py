import json
import contextlib
import io
import sys
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from scorer_review_contract import build_review_contract, generate_markdown, main  # noqa: E402


class ScorerReviewContractTests(unittest.TestCase):
    def test_contract_is_non_gated_and_execution_free(self):
        contract = build_review_contract()

        self.assertEqual(contract["contract_id"], "optional_scorer_review_contract_v1")
        self.assertFalse(contract["quality_gate_included"])
        self.assertFalse(contract["output_contract"]["may_change_quality_gate_result"])
        self.assertFalse(contract["output_contract"]["may_change_scorer_behavior"])
        self.assertTrue(contract["output_contract"]["requires_human_adjudication_before_promotion"])
        self.assertIn("No live provider calls.", contract["prohibited_behaviors"])
        self.assertIn("No local model calls.", contract["prohibited_behaviors"])

    def test_contract_can_reference_committed_public_safe_input(self):
        contract = build_review_contract(Path("reports/comparisons/scorer_calibration_summary.json"))

        self.assertEqual(contract["selected_input_path"], "reports/comparisons/scorer_calibration_summary.json")

    def test_generate_markdown_contains_non_gated_boundary(self):
        markdown = generate_markdown(build_review_contract())

        self.assertIn("# Optional Scorer Review Contract", markdown)
        self.assertIn("Quality gate included | false", markdown)
        self.assertIn("No live provider calls.", markdown)
        self.assertIn("No automatic scorer overrides", markdown)

    def test_writing_contract_requires_acknowledgement(self):
        with tempfile.TemporaryDirectory(dir=REPO_ROOT / "reports" / "comparisons") as temp_dir:
            output_path = Path(temp_dir) / "contract.json"

            stderr = io.StringIO()
            with contextlib.redirect_stderr(stderr):
                self.assertEqual(main(["--output-json", str(output_path)]), 2)
            self.assertFalse(output_path.exists())
            self.assertIn("--acknowledge-non-gated", stderr.getvalue())

            stdout = io.StringIO()
            with contextlib.redirect_stdout(stdout):
                self.assertEqual(main(["--output-json", str(output_path), "--acknowledge-non-gated"]), 0)
            self.assertTrue(output_path.exists())
            self.assertIn("optional scorer review contract JSON path", stdout.getvalue())
            self.assertEqual(
                json.loads(output_path.read_text(encoding="utf-8"))["contract_id"],
                "optional_scorer_review_contract_v1",
            )


if __name__ == "__main__":
    unittest.main()
