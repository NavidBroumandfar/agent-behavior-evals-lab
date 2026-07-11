"""Tests for the ground-truth labeling kit (structural-vs-judge disagreements)."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from ground_truth_labeling_kit import (  # noqa: E402
    LABELED_EXAMPLE_PATH,
    SAMPLE_PATH,
    LabelingKitError,
    build_worksheet,
    load_jsonl,
    summarize,
    validate_labels,
    validate_sample,
)


class LabelingKitTest(unittest.TestCase):
    def setUp(self) -> None:
        self.sample = load_jsonl(SAMPLE_PATH)
        self.labeled = load_jsonl(LABELED_EXAMPLE_PATH)

    def test_sample_is_all_disagreements(self) -> None:
        validate_sample(self.sample)  # raises if any record has structural == judge
        self.assertGreaterEqual(len(self.sample), 5)

    def test_blank_worksheet_does_not_validate(self) -> None:
        worksheet = build_worksheet(self.sample)
        with self.assertRaises(LabelingKitError):
            validate_labels(worksheet)

    def test_labeled_example_validates_and_summarizes(self) -> None:
        summary = summarize(self.labeled)
        self.assertEqual(summary["records"], len(self.labeled))
        self.assertTrue(0.0 <= summary["structural_vs_human_agreement"] <= 1.0)
        self.assertTrue(0.0 <= summary["judge_vs_human_agreement"] <= 1.0)

    def test_sample_contains_an_honest_judge_win(self) -> None:
        # Credibility: the kit must be able to side with the judge over the
        # structural check on at least one record.
        summary = summarize(self.labeled)
        self.assertTrue(summary["human_sided_with_judge_over_structural"])

    def test_invalid_label_is_rejected(self) -> None:
        bad = [dict(self.labeled[0], human_label="maybe")]
        with self.assertRaises(LabelingKitError):
            validate_labels(bad)

    def test_empty_rationale_is_rejected(self) -> None:
        bad = [dict(self.labeled[0], human_rationale="  ")]
        with self.assertRaises(LabelingKitError):
            validate_labels(bad)


if __name__ == "__main__":
    unittest.main()
