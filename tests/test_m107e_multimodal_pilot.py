from __future__ import annotations

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

from m107e_multimodal_pilot import (  # noqa: E402
    FIXTURE_SET_PATH,
    MultimodalPilotError,
    generate_multimodal_pilot,
)


class M107EMultimodalPilotTests(unittest.TestCase):
    def test_sample_fixture_generates_public_safe_multimodal_pilot_outputs(self) -> None:
        summary = generate_multimodal_pilot(FIXTURE_SET_PATH)

        self.assertEqual(summary["fixture_set_id"], "m107e_multimodal_public_safe_pilot")
        self.assertEqual(summary["media_asset_count"], 2)
        self.assertEqual(summary["modalities"], ["document", "image"])
        self.assertEqual(summary["saved_output_record_count"], 2)
        self.assertEqual(summary["reviewed_record_count"], 2)
        self.assertEqual(summary["customer_media_count"], 0)
        self.assertFalse(summary["live_model_execution_in_quality_gate"])
        self.assertFalse(summary["provider_calls_in_quality_gate"])

        report = json.loads((REPO_ROOT / summary["report_json_path"]).read_text(encoding="utf-8"))
        self.assertEqual(report["evidence_class"], "multimodal_saved_output")
        self.assertTrue(report["pilot_not_broad_multimodal_coverage"])
        self.assertEqual(report["customer_media_count"], 0)
        self.assertEqual(report["private_data_asset_count"], 0)
        self.assertIn("not broad multimodal coverage", report["claim_boundary"])

    def test_rejects_live_model_execution_in_quality_gate(self) -> None:
        fixture = self._load_fixture()
        fixture["live_model_execution_in_quality_gate"] = True

        self._assert_fixture_fails(fixture, "live_model_execution_in_quality_gate")

    def test_rejects_customer_media_asset(self) -> None:
        fixture = self._load_fixture()
        fixture["media_assets"][0]["customer_media"] = True

        self._assert_fixture_fails(fixture, "customer_media")

    def test_rejects_media_hash_mismatch(self) -> None:
        fixture = self._load_fixture()
        fixture["media_assets"][0]["sha256"] = "0" * 64

        self._assert_fixture_fails(fixture, "sha256 does not match")

    def test_rejects_claim_boundary_drift(self) -> None:
        fixture = self._load_fixture()
        fixture["saved_output_records"][0]["claim_boundary"] = "This proves broad multimodal production coverage."

        self._assert_fixture_fails(fixture, "claim_boundary")

    def test_rejects_private_or_credential_markers(self) -> None:
        fixture = self._load_fixture()
        fixture["saved_output_records"][0]["saved_model_output"] = "Saved output refers to private-evidence/demo.jsonl."

        self._assert_fixture_fails(fixture, "contains private")

    def _load_fixture(self) -> dict:
        return copy.deepcopy(json.loads(FIXTURE_SET_PATH.read_text(encoding="utf-8")))

    def _assert_fixture_fails(self, fixture: dict, message: str) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            fixture_path = Path(temp_dir) / "m107e_multimodal_fixture_set.example.json"
            fixture_path.write_text(json.dumps(fixture), encoding="utf-8")
            with self.assertRaisesRegex(MultimodalPilotError, message):
                generate_multimodal_pilot(fixture_path)


if __name__ == "__main__":
    unittest.main()
