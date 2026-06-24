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

from public_release_bundle import (  # noqa: E402
    DEFAULT_BUNDLE_PATH,
    PublicReleaseBundleError,
    validate_public_release_bundle,
)


def load_valid_bundle():
    return json.loads(DEFAULT_BUNDLE_PATH.read_text(encoding="utf-8"))


def write_json(path, value):
    path.write_text(json.dumps(value, sort_keys=True, indent=2) + "\n", encoding="utf-8")


class PublicReleaseBundleTests(unittest.TestCase):
    def test_committed_bundle_validates(self):
        summary = validate_public_release_bundle()

        self.assertEqual(summary["bundle_path"], "traces/external/public_release_bundle.example.json")
        self.assertEqual(summary["schema_path"], "schemas/public_release_bundle.schema.json")
        self.assertEqual(summary["bundle_id"], "m87_claim_locked_public_release_bundle")
        self.assertEqual(summary["status"], "public_safe_release_bundle")
        self.assertEqual(summary["release_label"], "public_safe_local_open_weight_ranking")
        self.assertEqual(summary["ranked_targets"], 6)
        self.assertEqual(summary["blocked_claims"], 8)

    def test_live_execution_in_quality_gate_is_rejected(self):
        bundle = load_valid_bundle()
        bundle["quality_gate"]["live_local_execution_in_quality_gate"] = True

        self.assert_bundle_fails(bundle, "live_local_execution_in_quality_gate must equal False")

    def test_release_scope_must_remain_local_open_weight(self):
        bundle = load_valid_bundle()
        bundle["release_scope"]["release_label"] = "cloud_model_ranking"

        self.assert_bundle_fails(bundle, "release_label must equal")

    def test_statement_must_name_ranked_models(self):
        bundle = load_valid_bundle()
        bundle["approved_release_statement"]["summary"] = "The committed report may be described as a local ranking."

        self.assert_bundle_fails(bundle, "missing required snippet")

    def test_required_qualifier_must_block_production_claims(self):
        bundle = load_valid_bundle()
        bundle["approved_release_statement"]["required_qualifier"] = "This is not a cloud-model ranking."

        self.assert_bundle_fails(bundle, "missing required snippet: hosted-provider comparison")

    def test_ranking_rows_must_match_report(self):
        bundle = load_valid_bundle()
        bundle["ranking_rows"][0]["sample_size"] = 209

        self.assert_bundle_fails(bundle, "sample_size does not match source report")

    def test_missing_m86_blocked_claim_is_rejected(self):
        bundle = load_valid_bundle()
        bundle["blocked_claims"] = [
            claim for claim in bundle["blocked_claims"] if claim["claim_id"] != "production_safety"
        ]

        self.assert_bundle_fails(bundle, "missing blocked claims: production_safety")

    def test_blocked_claim_instruction_must_be_negative(self):
        bundle = load_valid_bundle()
        bundle["blocked_claims"][0]["release_instruction"] = "Describe this release as a cloud-model ranking."

        self.assert_bundle_fails(bundle, "release_instruction must start with 'Do not '")

    def test_raw_source_path_is_rejected(self):
        bundle = load_valid_bundle()
        bundle["source_paths"].append("traces/raw/m81_mistral_latest_extended.local.jsonl")

        self.assert_bundle_fails(bundle, "must not reference raw or private local artifacts")

    def test_duplicate_release_artifact_is_rejected(self):
        bundle = load_valid_bundle()
        bundle["release_artifacts"].append(copy.deepcopy(bundle["release_artifacts"][0]))

        self.assert_bundle_fails(bundle, "duplicate value")

    def assert_bundle_fails(self, bundle, message):
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "public_release_bundle.example.json"
            write_json(path, bundle)

            with self.assertRaisesRegex(PublicReleaseBundleError, message):
                validate_public_release_bundle(path)


if __name__ == "__main__":
    unittest.main()
