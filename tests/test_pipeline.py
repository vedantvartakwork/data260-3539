from __future__ import annotations

import unittest

from agents_demo import PipelineValidationError, normalize_tag, validate_publish, word_count


class PublishValidationTests(unittest.TestCase):
    def test_accepts_required_shape(self) -> None:
        value = {
            "tags": ["undeclared almonds", "spinach recall", "allergy warning"],
            "summary": "Selected spinach bags are recalled because they may contain undeclared almonds.",
        }
        self.assertEqual(validate_publish(value), value)

    def test_rejects_duplicate_tags_ignoring_case_and_whitespace(self) -> None:
        with self.assertRaises(PipelineValidationError):
            validate_publish(
                {
                    "tags": ["Spinach Recall", " spinach   recall ", "allergy warning"],
                    "summary": "A product recall warns customers about undeclared almonds.",
                }
            )

    def test_rejects_summary_over_25_words(self) -> None:
        summary = " ".join(["word"] * 26) + "."
        self.assertEqual(word_count(summary), 26)
        with self.assertRaises(PipelineValidationError):
            validate_publish({"tags": ["one", "two", "three"], "summary": summary})

    def test_tag_normalization(self) -> None:
        self.assertEqual(normalize_tag("  Allergy   Warning "), "allergy warning")


if __name__ == "__main__":
    unittest.main()

