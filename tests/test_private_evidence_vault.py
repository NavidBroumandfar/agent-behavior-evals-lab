import json
import sys
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from private_evidence_vault import (  # noqa: E402
    DEFAULT_MANIFEST_PATH,
    PrivateEvidenceVaultError,
    generate_private_evidence_vault_summary,
    validate_private_evidence_manifest,
    validate_promotion_preflight,
)


def load_valid_manifest():
    return json.loads(DEFAULT_MANIFEST_PATH.read_text(encoding="utf-8"))


def write_json(path, value):
    path.write_text(json.dumps(value, sort_keys=True, indent=2) + "\n", encoding="utf-8")


class PrivateEvidenceVaultTests(unittest.TestCase):
    def test_committed_manifest_generates_public_safe_boundary_reports(self):
        with tempfile.TemporaryDirectory(dir=REPO_ROOT / "reports" / "comparisons") as temp_dir:
            summary_json = Path(temp_dir) / "private_evidence_vault_summary.json"
            summary_report = Path(temp_dir) / "private_evidence_vault_summary.md"

            summary = generate_private_evidence_vault_summary(
                DEFAULT_MANIFEST_PATH,
                summary_json_path=summary_json,
                summary_report_path=summary_report,
            )

            self.assertEqual(summary["manifest_id"], "m66_private_evidence_vault")
            self.assertEqual(summary["evidence_class"], "private_audit_metadata_public_safe")
            self.assertTrue(summary["public_safe_fake_metadata_only"])
            self.assertEqual(summary["record_counts"]["private_record_metadata_count"], 2)
            self.assertEqual(summary["record_counts"]["promotion_candidate_count"], 1)
            self.assertEqual(summary["record_counts"]["promotion_allowed_count"], 0)
            self.assertFalse(summary["vault"]["raw_private_records_committable"])
            self.assertFalse(summary["vault"]["private_reports_committable"])
            self.assertTrue(summary["vault"]["vault_root_gitignored"])
            self.assertTrue(summary["vault"]["private_reports_root_gitignored"])
            self.assertTrue(summary_json.exists())
            self.assertIn("Private Evidence Vault Boundary Summary", summary_report.read_text(encoding="utf-8"))

    def test_private_evidence_ingestion_in_quality_gate_is_rejected(self):
        manifest = load_valid_manifest()
        manifest["quality_gate"]["private_evidence_ingestion_in_quality_gate"] = True

        self.assert_manifest_fails(manifest, "private_evidence_ingestion_in_quality_gate must equal False")

    def test_missing_gitignore_pattern_is_rejected(self):
        manifest = load_valid_manifest()
        manifest["vault_controls"]["vault_root"] = "not_ignored_private_evidence/"
        manifest["private_records"][0]["artifact_path"] = "not_ignored_private_evidence/fake/raw_trace.local.jsonl"
        manifest["private_records"][1]["artifact_path"] = "not_ignored_private_evidence/fake/tool_summary.local.jsonl"
        manifest["private_records"][0]["redaction_metadata"]["redaction_notes_path"] = (
            "not_ignored_private_evidence/fake/redaction_notes.local.json"
        )
        manifest["private_records"][1]["redaction_metadata"]["redaction_notes_path"] = (
            "not_ignored_private_evidence/fake/redaction_notes.local.json"
        )

        self.assert_manifest_fails(manifest, "requires \\.gitignore pattern 'not_ignored_private_evidence/'")

    def test_promotion_candidate_requires_redaction_metadata(self):
        manifest = load_valid_manifest()
        manifest["private_records"][1]["redaction_metadata"]["metadata_present"] = False

        self.assert_manifest_fails(manifest, "refuses promotion without explicit redaction metadata")

    def test_m66_rejects_promotion_allowed_records(self):
        manifest = load_valid_manifest()
        manifest["private_records"][1]["redaction_metadata"]["promotion_allowed"] = True

        self.assert_manifest_fails(manifest, "promotion_allowed must be false until M67")

    def test_private_audit_report_label_is_required(self):
        manifest = load_valid_manifest()
        manifest["private_records"][0]["private_audit_report_label"] = "public_report"

        self.assert_manifest_fails(manifest, "must be one of: private_audit_report")

    def test_explicit_promotion_preflight_refuses_without_reviewer_signoff(self):
        manifest = load_valid_manifest()
        record = manifest["private_records"][1]

        with self.assertRaisesRegex(PrivateEvidenceVaultError, "refuses promotion without reviewer signoff"):
            validate_promotion_preflight(record, "fake_private_tool_summary_001")

    def assert_manifest_fails(self, manifest, message):
        with tempfile.TemporaryDirectory(dir=REPO_ROOT / "traces" / "external") as temp_dir:
            path = Path(temp_dir) / "private_evidence_vault_manifest.example.json"
            write_json(path, manifest)

            with self.assertRaisesRegex(PrivateEvidenceVaultError, message):
                validate_private_evidence_manifest(path)


if __name__ == "__main__":
    unittest.main()
