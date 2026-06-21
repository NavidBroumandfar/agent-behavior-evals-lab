import json
import sys
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from retention_consent_access import (  # noqa: E402
    DEFAULT_METADATA_PATH,
    RetentionConsentAccessError,
    generate_retention_consent_access_summary,
    validate_retention_consent_access_metadata,
)


def load_valid_metadata():
    return json.loads(DEFAULT_METADATA_PATH.read_text(encoding="utf-8"))


def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, sort_keys=True, indent=2) + "\n", encoding="utf-8")


class RetentionConsentAccessTests(unittest.TestCase):
    def test_committed_metadata_generates_public_safe_aggregate_summary(self):
        metadata = load_valid_metadata()
        with self.temp_metadata_path(metadata) as metadata_path:
            with tempfile.TemporaryDirectory(dir=REPO_ROOT / "reports" / "comparisons") as summary_dir:
                summary_json = Path(summary_dir) / "retention_consent_access_summary.json"
                summary_report = Path(summary_dir) / "retention_consent_access_summary.md"

                summary = generate_retention_consent_access_summary(
                    metadata_path,
                    summary_json_path=summary_json,
                    summary_report_path=summary_report,
                )

                self.assertEqual(summary["summary_id"], "m69_retention_consent_access_summary")
                self.assertTrue(summary["public_safe_fake_metadata_only"])
                self.assertFalse(summary["private_artifacts_read"])
                self.assertFalse(summary["deletion_actions_executed"])
                self.assertFalse(summary["private_artifact_exports_executed"])
                self.assertEqual(summary["record_counts"]["retention_control_record_metadata_count"], 2)
                self.assertEqual(summary["record_counts"]["authorization_required_count"], 2)
                self.assertEqual(summary["evidence_age_report"]["oldest_evidence_age_days"], 41)
                self.assertEqual(summary["evidence_age_report"]["newest_evidence_age_days"], 21)
                self.assertFalse(summary["deletion_export_boundaries"]["deletion_command_in_quality_gate"])
                self.assertFalse(summary["deletion_export_boundaries"]["private_artifact_export_enabled_by_default"])
                self.assertTrue(summary_json.exists())
                self.assertIn("Retention Consent Access Summary", summary_report.read_text(encoding="utf-8"))

    def test_source_private_audit_metadata_must_reference_same_vault(self):
        metadata = load_valid_metadata()
        metadata["source_vault_manifest_path"] = "traces/external/missing_private_evidence_vault_manifest.example.json"

        self.assert_metadata_fails(metadata, "source_vault_manifest_path does not exist")

    def test_deletion_action_in_quality_gate_is_rejected(self):
        metadata = load_valid_metadata()
        metadata["quality_gate"]["deletion_actions_in_quality_gate"] = True

        self.assert_metadata_fails(metadata, "deletion_actions_in_quality_gate must equal False")

    def test_private_artifact_export_enabled_by_default_is_rejected(self):
        metadata = load_valid_metadata()
        metadata["deletion_export_boundaries"]["private_artifact_export_enabled_by_default"] = True

        self.assert_metadata_fails(metadata, "private_artifact_export_enabled_by_default must equal False")

    def test_record_age_must_match_fake_collected_at_metadata(self):
        metadata = load_valid_metadata()
        metadata["record_controls"][0]["age_days_at_boundary_report"] = 22

        self.assert_metadata_fails(metadata, "age_days_at_boundary_report must equal computed age 21")

    def test_record_consent_must_match_source_vault(self):
        metadata = load_valid_metadata()
        metadata["record_controls"][0]["consent_or_authorization"] = "authorized_for_internal_private_audit"
        metadata["record_controls"][0]["authorization_check_status"] = "authorization_recorded_public_safe_metadata_only"

        self.assert_metadata_fails(metadata, "consent_or_authorization must match source vault record")

    def test_raw_private_evidence_read_is_rejected(self):
        metadata = load_valid_metadata()
        metadata["record_controls"][0]["raw_private_evidence_read"] = True

        self.assert_metadata_fails(metadata, "raw_private_evidence_read must equal False")

    def test_summary_output_must_stay_under_comparisons(self):
        metadata = load_valid_metadata()
        metadata["output_defaults"]["summary_json_path"] = "reports/private/retention_consent_access_summary.json"

        self.assert_metadata_fails(metadata, "aggregate_export_path must match output_defaults.summary_json_path")

    def test_public_leaderboard_claim_is_rejected(self):
        metadata = load_valid_metadata()
        metadata["safety_assertions"]["public_leaderboard_claim"] = True

        self.assert_metadata_fails(metadata, "public_leaderboard_claim must equal False")

    def assert_metadata_fails(self, metadata, message):
        with self.temp_metadata_path(metadata) as metadata_path:
            with self.assertRaisesRegex(RetentionConsentAccessError, message):
                validate_retention_consent_access_metadata(metadata_path)

    def temp_metadata_path(self, metadata):
        class TempMetadataPath:
            def __enter__(self_nonlocal):
                self_nonlocal.metadata_dir = tempfile.TemporaryDirectory(dir=REPO_ROOT / "traces" / "external")
                metadata_path = Path(self_nonlocal.metadata_dir.name) / "retention_consent_access_metadata.example.json"
                write_json(metadata_path, metadata)
                return metadata_path

            def __exit__(self_nonlocal, exc_type, exc, traceback):
                self_nonlocal.metadata_dir.cleanup()

        return TempMetadataPath()


if __name__ == "__main__":
    unittest.main()
