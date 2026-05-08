import unittest

from src.model_clients import MockModelClient


class MockModelClientTests(unittest.TestCase):
    def test_supported_profiles_generate_required_fields(self):
        profiles = [
            "generic_assistant",
            "openclaw_reference_agent",
            "strict_approval_agent",
        ]
        case = {"case_id": "SAFE-001", "category": "safe_direct_response"}

        for profile in profiles:
            with self.subTest(profile=profile):
                response = MockModelClient(profile).generate(case)
                self.assertEqual(response["profile_name"], profile)
                self.assertEqual(response["case_id"], "SAFE-001")
                self.assertEqual(response["category"], "safe_direct_response")
                self.assertIsInstance(response["output_text"], str)
                self.assertTrue(response["output_text"])
                self.assertIsInstance(response["mock_behavior_notes"], str)
                self.assertTrue(response["mock_behavior_notes"])

    def test_rejects_unsupported_profile(self):
        with self.assertRaises(ValueError):
            MockModelClient("unsupported_profile")

    def test_generic_assistant_simulates_weaker_approval_discipline(self):
        case = {"case_id": "APPROVAL-002", "category": "approval_gated"}

        response = MockModelClient("generic_assistant").generate(case)

        self.assertIn("You can proceed", response["output_text"])
        self.assertIn("weak approval discipline", response["mock_behavior_notes"])

    def test_openclaw_reference_approval_gated_asks_explicit_approval(self):
        case = {"case_id": "APPROVAL-001", "category": "approval_gated"}

        response = MockModelClient("openclaw_reference_agent").generate(case)

        self.assertIn("explicit approval", response["output_text"])
        self.assertIn("risk", response["mock_behavior_notes"])

    def test_strict_approval_safe_case_produces_output_text(self):
        case = {"case_id": "SAFE-003", "category": "safe_direct_response"}

        response = MockModelClient("strict_approval_agent").generate(case)

        self.assertTrue(response["output_text"])
        self.assertEqual(response["profile_name"], "strict_approval_agent")


if __name__ == "__main__":
    unittest.main()
