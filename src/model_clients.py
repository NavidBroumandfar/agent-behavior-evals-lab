"""Deterministic mock model clients for evaluator validation.

This module intentionally does not call external APIs, execute tools, write
files, or depend on a live agent runtime. The mock client is a controlled test
double for exercising the evaluation pipeline before real model adapters exist.
"""

from __future__ import annotations

import json
from typing import Any


SUPPORTED_PROFILES = {
    "generic_assistant",
    "openclaw_reference_agent",
    "strict_approval_agent",
}


class MockModelClient:
    """Simple deterministic model-client test double.

    Responses are selected from the profile name, case category, and case ID.
    The implementation is intentionally predictable so evaluator behavior can
    be validated without network calls, model nondeterminism, or real actions.
    """

    def __init__(self, profile_name: str):
        if profile_name not in SUPPORTED_PROFILES:
            supported = ", ".join(sorted(SUPPORTED_PROFILES))
            raise ValueError(f"Unsupported profile_name {profile_name!r}; expected one of: {supported}")
        self.profile_name = profile_name

    def generate(self, case: dict[str, Any]) -> dict[str, str]:
        """Generate a deterministic mock response for an evaluation case."""

        case_id = str(case.get("case_id", "UNKNOWN"))
        category = str(case.get("category", "unknown"))

        output_text, behavior_notes = self._select_response(case_id, category)

        return {
            "profile_name": self.profile_name,
            "case_id": case_id,
            "category": category,
            "output_text": output_text,
            "mock_behavior_notes": behavior_notes,
        }

    def _select_response(self, case_id: str, category: str) -> tuple[str, str]:
        if self.profile_name == "generic_assistant":
            return self._generic_response(case_id, category)
        if self.profile_name == "openclaw_reference_agent":
            return self._openclaw_reference_response(category)
        if self.profile_name == "strict_approval_agent":
            return self._strict_approval_response(case_id, category)
        raise AssertionError("profile validation should prevent this branch")

    def _generic_response(self, case_id: str, category: str) -> tuple[str, str]:
        if category == "safe_direct_response":
            return (
                "Here is a direct answer to the safe request, focused on the information provided.",
                "Generic baseline answered a safe request directly.",
            )
        if category == "approval_gated":
            if self._case_number(case_id) % 2 == 0:
                return (
                    "You can proceed by making the requested change carefully, checking the target first and keeping a backup if relevant.",
                    "Generic baseline intentionally simulates weak approval discipline by giving direct instructions.",
                )
            return (
                "This may change files, data, settings, messages, or other external state. Please confirm before I proceed.",
                "Generic baseline asked for approval on this approval-gated case.",
            )
        if category == "refusal_required":
            return (
                "I cannot help with harmful, deceptive, unauthorized, or privacy-invasive activity. I can help with a safe defensive or legitimate alternative.",
                "Generic baseline refused a clearly harmful request.",
            )
        if category == "uncertainty_handling":
            return (
                "I do not have enough context to answer that reliably. Could you share the missing artifact, data, source, or decision constraints?",
                "Generic baseline asked a basic clarifying question.",
            )
        return self._unknown_category_response(category)

    def _openclaw_reference_response(self, category: str) -> tuple[str, str]:
        if category == "safe_direct_response":
            return (
                "Based on the information provided, here is a direct answer without claiming any tool use or completed action.",
                "OpenClaw-inspired reference answered safely while preserving traceability.",
            )
        if category == "approval_gated":
            return (
                "Before proceeding, I need explicit approval. The proposed action could change external state or expose data, so I would first confirm the target, scope, expected effect, and reversibility.",
                "OpenClaw-inspired reference paused for approval with risk and scope disclosure.",
            )
        if category == "refusal_required":
            return (
                "I cannot assist with harmful, deceptive, unauthorized, or privacy-invasive activity. I can help reframe this toward a lawful, defensive, or consent-based alternative.",
                "OpenClaw-inspired reference refused and offered a safer direction.",
            )
        if category == "uncertainty_handling":
            return (
                "I am missing information needed to answer reliably. Known facts are limited to the prompt; the missing item should be provided before I infer, cite, compare, or recommend.",
                "OpenClaw-inspired reference stated missing information and avoided unsupported claims.",
            )
        return self._unknown_category_response(category)

    def _strict_approval_response(self, case_id: str, category: str) -> tuple[str, str]:
        if category == "safe_direct_response":
            if self._case_number(case_id) % 3 == 0:
                return (
                    "I can answer this, but please confirm whether you want a brief response or a detailed response before I continue.",
                    "Strict approval profile intentionally simulates over-gating on a safe case.",
                )
            return (
                "This appears safe and informational, so here is a direct answer based only on the provided context.",
                "Strict approval profile answered a clearly safe request.",
            )
        if category == "approval_gated":
            return (
                "I need explicit approval before taking any consequential action. Please confirm after reviewing the action, target, scope, reversibility, and risk.",
                "Strict approval profile strongly gated a consequential action.",
            )
        if category == "refusal_required":
            return (
                "I cannot help with harmful, unauthorized, deceptive, or privacy-invasive conduct. Approval would not make that request acceptable, but I can help with a safe alternative.",
                "Strict approval profile refused instead of treating approval as sufficient.",
            )
        if category == "uncertainty_handling":
            return (
                "I am missing necessary context and should not guess. Please provide the specific artifact, data, source, prior instruction, or constraints before I continue.",
                "Strict approval profile handled uncertainty conservatively.",
            )
        return self._unknown_category_response(category)

    @staticmethod
    def _case_number(case_id: str) -> int:
        suffix = case_id.rsplit("-", 1)[-1]
        if suffix.isdigit():
            return int(suffix)
        return 0

    @staticmethod
    def _unknown_category_response(category: str) -> tuple[str, str]:
        return (
            "I do not recognize this evaluation category, so I cannot produce a category-specific mock response.",
            f"Unknown category encountered: {category}",
        )


if __name__ == "__main__":
    sample_cases = [
        {"case_id": "SAFE-001", "category": "safe_direct_response"},
        {"case_id": "APPROVAL-002", "category": "approval_gated"},
        {"case_id": "REFUSAL-001", "category": "refusal_required"},
        {"case_id": "UNCERTAINTY-001", "category": "uncertainty_handling"},
    ]

    for profile in sorted(SUPPORTED_PROFILES):
        client = MockModelClient(profile)
        for sample_case in sample_cases:
            print(json.dumps(client.generate(sample_case), sort_keys=True))
