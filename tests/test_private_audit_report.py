import json
import sys
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from private_audit_report import (  # noqa: E402
    DEFAULT_METADATA_PATH,
    PrivateAuditReportError,
    generate_private_audit_report,
    validate_private_audit_report_metadata,
)


def load_valid_metadata():
    return json.loads(DEFAULT_METADATA_PATH.read_text(encoding="utf-8"))


def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, sort_keys=True, indent=2) + "\n", encoding="utf-8")


DEFAULT_PRIVATE_JSON_PATH = "reports/private/m68_private_audit_report.local.json"
DEFAULT_PRIVATE_MARKDOWN_PATH = "reports/private/m68_private_audit_report.local.md"


class PrivateAuditReportTests(unittest.TestCase):
    def test_committed_metadata_generates_local_private_report_and_public_summary(self):
        metadata = load_valid_metadata()
        with self.temp_metadata_path(metadata) as metadata_path:
            with tempfile.TemporaryDirectory(dir=REPO_ROOT / "reports" / "comparisons") as summary_dir:
                summary_json = Path(summary_dir) / "private_audit_report_boundary_summary.json"
                summary_report = Path(summary_dir) / "private_audit_report_boundary_summary.md"

                summary = generate_private_audit_report(
                    metadata_path,
                    summary_json_path=summary_json,
                    summary_report_path=summary_report,
                )

                private_json_path = REPO_ROOT / metadata["output_defaults"]["json_path"]
                private_report_path = REPO_ROOT / metadata["output_defaults"]["markdown_path"]
                private_report = json.loads(private_json_path.read_text(encoding="utf-8"))

                self.assertEqual(summary["summary_id"], "m68_private_audit_report_boundary_summary")
                self.assertEqual(summary["report_label"], "private_audit_report")
                self.assertEqual(summary["record_counts"]["included_private_record_metadata_count"], 2)
                self.assertEqual(summary["record_counts"]["promotion_candidate_count"], 1)
                self.assertTrue(summary["public_safe_fake_metadata_only"])
                self.assertFalse(summary["private_artifacts_read"])
                self.assertFalse(summary["public_leaderboard_eligible"])
                self.assertFalse(summary["production_safety_claim"])
                self.assertFalse(summary["third_party_reproducibility_claim"])
                self.assertFalse(summary["private_audit_overclaim"])
                self.assertFalse(summary["aggregate_export_policy"]["enabled_by_default"])
                self.assertTrue(summary["aggregate_export_policy"]["aggregate_only"])
                self.assertTrue(private_json_path.exists())
                self.assertTrue(private_report_path.exists())
                self.assertEqual(private_report["report_label"], "private_audit_report")
                self.assertFalse(private_report["output_boundary"]["artifact_paths_included"])
                self.assertNotIn("private_evidence/", private_json_path.read_text(encoding="utf-8"))
                self.assertIn("Private Audit Report Boundary Summary", summary_report.read_text(encoding="utf-8"))

    def test_report_label_is_required(self):
        metadata = load_valid_metadata()
        metadata["report_label"] = "public_report"

        self.assert_metadata_fails(metadata, "must be one of: private_audit_report")

    def test_private_output_must_stay_under_ignored_private_report_root(self):
        metadata = load_valid_metadata()
        metadata["output_defaults"]["json_path"] = "reports/comparisons/private_audit_report.local.json"

        self.assert_metadata_fails(metadata, "output_defaults.json_path must stay under reports/private")

    def test_raw_private_evidence_claim_is_rejected(self):
        metadata = load_valid_metadata()
        metadata["report_controls"]["report_contains_raw_private_evidence"] = True

        self.assert_metadata_fails(metadata, "report_contains_raw_private_evidence must equal False")

    def test_public_leaderboard_claim_is_rejected(self):
        metadata = load_valid_metadata()
        metadata["safety_assertions"]["public_leaderboard_claim"] = True

        self.assert_metadata_fails(metadata, "public_leaderboard_claim must equal False")

    def test_included_records_must_reference_source_vault(self):
        metadata = load_valid_metadata()
        metadata["included_private_record_ids"] = ["missing_private_record"]

        self.assert_metadata_fails(metadata, "must reference source vault private_records")

    def assert_metadata_fails(self, metadata, message):
        with self.temp_metadata_path(metadata) as metadata_path:
            with self.assertRaisesRegex(PrivateAuditReportError, message):
                validate_private_audit_report_metadata(metadata_path)

    def temp_metadata_path(self, metadata):
        class TempMetadataPath:
            def __enter__(self_nonlocal):
                self_nonlocal.private_parent = REPO_ROOT / "reports" / "private"
                self_nonlocal.private_parent.mkdir(parents=True, exist_ok=True)
                self_nonlocal.private_dir = tempfile.TemporaryDirectory(dir=self_nonlocal.private_parent)
                self_nonlocal.metadata_dir = tempfile.TemporaryDirectory(dir=REPO_ROOT / "traces" / "external")
                private_dir = Path(self_nonlocal.private_dir.name)
                metadata_path = Path(self_nonlocal.metadata_dir.name) / "private_audit_report_metadata.example.json"
                if metadata["output_defaults"]["json_path"] == DEFAULT_PRIVATE_JSON_PATH:
                    metadata["output_defaults"]["json_path"] = str(
                        (private_dir / "private_audit_report.local.json").relative_to(REPO_ROOT)
                    )
                if metadata["output_defaults"]["markdown_path"] == DEFAULT_PRIVATE_MARKDOWN_PATH:
                    metadata["output_defaults"]["markdown_path"] = str(
                        (private_dir / "private_audit_report.local.md").relative_to(REPO_ROOT)
                    )
                write_json(metadata_path, metadata)
                return metadata_path

            def __exit__(self_nonlocal, exc_type, exc, traceback):
                self_nonlocal.metadata_dir.cleanup()
                self_nonlocal.private_dir.cleanup()

        return TempMetadataPath()


if __name__ == "__main__":
    unittest.main()
