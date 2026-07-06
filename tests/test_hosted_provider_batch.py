import json
import sys
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from hosted_provider_batch import (  # noqa: E402
    DEFAULT_METADATA_PATH,
    HostedProviderBatchError,
    generate_hosted_provider_batch_summary,
    validate_hosted_provider_batch_metadata,
)


def load_valid_metadata():
    return json.loads(DEFAULT_METADATA_PATH.read_text(encoding="utf-8"))


def write_json(path, value):
    path.write_text(json.dumps(value, sort_keys=True, indent=2) + "\n", encoding="utf-8")


class HostedProviderBatchTests(unittest.TestCase):
    def test_committed_metadata_generates_public_safe_summary(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            report_json = Path(temp_dir) / "hosted_provider_batch_summary.json"
            report_md = Path(temp_dir) / "hosted_provider_batch_summary.md"

            summary = generate_hosted_provider_batch_summary(
                report_json_path=report_json,
                report_markdown_path=report_md,
            )

            self.assertEqual(summary["summary_id"], "m75_hosted_provider_batch_summary")
            self.assertEqual(summary["provider"], "openai")
            self.assertEqual(summary["batch"]["batch_status"], "not_submitted")
            self.assertFalse(summary["publication_state"]["hosted_report_ready"])
            self.assertFalse(summary["publication_state"]["local_open_weight_ranking_claim_allowed"])
            self.assertTrue(report_json.exists())
            self.assertIn("Hosted Provider Batch Summary", report_md.read_text(encoding="utf-8"))

    def test_provider_calls_in_quality_gate_are_rejected(self):
        metadata = load_valid_metadata()
        metadata["quality_gate"]["provider_calls_in_quality_gate"] = True

        self.assert_metadata_fails(metadata, "provider_calls_in_quality_gate must equal False")

    def test_batch_submission_is_rejected(self):
        metadata = load_valid_metadata()
        metadata["batch"]["submitted"] = True

        self.assert_metadata_fails(metadata, "submitted")

    def test_committed_request_payload_is_rejected(self):
        metadata = load_valid_metadata()
        metadata["payload_hashes"]["request_payload_committed"] = True

        self.assert_metadata_fails(metadata, "request_payload_committed")

    def test_mixed_provider_comparison_is_rejected(self):
        metadata = load_valid_metadata()
        metadata["separation_boundary"]["mixed_provider_comparison_allowed"] = True

        self.assert_metadata_fails(metadata, "mixed_provider_comparison_allowed")

    def test_cloud_label_placeholder_is_rejected(self):
        metadata = load_valid_metadata()
        metadata["model"] = "cloud-model-placeholder"

        self.assert_metadata_fails(metadata, "neutral placeholder")

    def assert_metadata_fails(self, metadata, message):
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "hosted_provider_batch_metadata.example.json"
            write_json(path, metadata)

            with self.assertRaisesRegex(HostedProviderBatchError, message):
                validate_hosted_provider_batch_metadata(path)


if __name__ == "__main__":
    unittest.main()
